import json
import time
from flask import Response, stream_with_context
from Pan123 import Pan123
from utils import getStringHash
from api.api_utils import custom_secure_filename_part, handle_database_storage
from queueManager import QUEUE_MANAGER

from getGlobalLogger import logger

def handle_export_request(data):
    username = data.get('username')
    password = data.get('password')
    home_file_path_str = data.get('homeFilePath', '0')
    user_specified_base_name_raw = data.get('userSpecifiedBaseName', '').strip()
    generate_short_code_flag = data.get('generateShortCode', False)
    share_project_flag = data.get('shareProject', False)

    if not username or not password:
        return Response(json.dumps({"isFinish": False, "message": "用户名和密码不能为空。"}), 
                        mimetype='application/x-ndjson', status=400)
    if share_project_flag and not user_specified_base_name_raw:
        return Response(json.dumps({"isFinish": False, "message": "加入资源共享计划时，必须填写根目录名 (分享名)。"}),
                        mimetype='application/x-ndjson', status=400)
    if share_project_flag:
        generate_short_code_flag = True

    task_description = f"导出_{username[:5]}..._{user_specified_base_name_raw[:10] if user_specified_base_name_raw else '默认名'}"
    task_id = QUEUE_MANAGER.add_task(task_name=task_description)
    # logger.info(f"导出任务 {task_id} ({task_description}) 已添加到队列。") # queue_manager内部已有日志

    def generate_export_stream_with_queue():
        initial_greeting_sent = False
        processed_by_queue = False 
        login_success_flag = False # 必须在 try 外部声明以便 finally 块访问
        driver = None # 同样，为了注销

        try:
            logger.info(f"导出任务 {task_id}: 开始排队/处理流程。")
            # 阶段1: 排队等待
            while not processed_by_queue:
                position, is_another_processing = QUEUE_MANAGER.get_task_position_and_is_processing_another(task_id)
                
                logger.debug(f"导出任务 {task_id}: 队列检查 - 位置 {position}, 其他处理中: {is_another_processing}")

                if position == -2: 
                    yield f"{json.dumps({'isFinish': False, 'message': '任务ID无效、已过期或已被取消，请重试。'})}\n"
                    logger.warning(f"导出任务 {task_id} 在队列中未找到或已失效。")
                    return 

                if position == 0 and not is_another_processing:
                    if not initial_greeting_sent:
                        yield f"{json.dumps({'isFinish': None, 'message': '恭喜! 哥们运气真好, 前面竟然 0 人排队! 小小后端, 快给这位爷伺候起来，优先服务!'})}\n"
                        initial_greeting_sent = True
                    
                    if QUEUE_MANAGER.attempt_to_start_processing(task_id):
                        yield f"{json.dumps({'isFinish': None, 'message': '恭喜义父, 轮到您嘞! 操作即将开始...'})}\n"
                        processed_by_queue = True 
                        # logger.info(f"导出任务 {task_id} 开始执行实际操作。") # queue_manager内部已有日志
                        break 
                    else:
                        logger.warning(f"导出任务 {task_id}: 在队首但 attempt_to_start_processing 失败。可能是并发或任务已不在队列。")
                        yield f"{json.dumps({'isFinish': None, 'message': '系统正忙或任务状态变更，仍在尝试获取执行权...'})}\n"
                
                elif position >= 0 :
                    people_ahead = position 
                    yield f"{json.dumps({'isFinish': None, 'message': f'正在排队中... 前面还有 {people_ahead} 人。'})}\n"
                    initial_greeting_sent = True
                
                else: 
                    yield f"{json.dumps({'isFinish': False, 'message': f'未知的队列状态 ({position})，请重试。'})}\n"
                    logger.error(f"导出任务 {task_id} 遇到非预期的队列状态 {position}。")
                    return

                if not processed_by_queue:
                    time.sleep(5)

            # 阶段2: 实际的123网盘操作 
            if not processed_by_queue:
                logger.warning(f"任务 {task_id} (导出) 退出排队循环但 processed_by_queue 仍为 false，任务不执行。")
                return

            try:
                parent_file_id_internal = int(home_file_path_str)
            except ValueError:
                parent_file_id_internal = home_file_path_str  

            cleaned_db_root_name = custom_secure_filename_part(user_specified_base_name_raw)
            if generate_short_code_flag and not cleaned_db_root_name: 
                cleaned_db_root_name = f"导出的分享_{int(time.time())}"

            driver = Pan123()
            final_b64_string_data = None
            short_share_code_result = None
            pan123_op_successful = False

            yield f"{json.dumps({'isFinish': None, 'message': '准备登录...'})}\n"
            login_success_flag = driver.doLogin(username=username, password=password)
            if not login_success_flag:
                yield f"{json.dumps({'isFinish': False, 'message': '登录失败，请检查用户名和密码。'})}\n"
                return 

            yield f"{json.dumps({'isFinish': None, 'message': '登录成功，开始导出文件列表...'})}\n"
            
            for state in driver.exportFiles(parentFileId=parent_file_id_internal):
                logger.debug(f"任务 {task_id} exportFiles state: {json.dumps(state, ensure_ascii=False)}")
                if state.get("isFinish") is True:
                    final_b64_string_data = state["message"]
                    pan123_op_successful = True
                    break 
                elif state.get("isFinish") is False: 
                    yield f"{json.dumps(state)}\n" 
                    pan123_op_successful = False 
                    break 
                else: 
                    yield f"{json.dumps(state)}\n"
            
            if not pan123_op_successful and final_b64_string_data is None:
                 if pan123_op_successful is not True: # 避免重复发送错误
                    yield f"{json.dumps({'isFinish': False, 'message': '未能从123网盘获取文件数据，或操作提前终止。'})}\n"

            if pan123_op_successful: 
                yield f"{json.dumps({'isFinish': None, 'message': '文件列表从123网盘导出成功。正在进一步处理...'})}\n"
                if generate_short_code_flag: 
                    yield f"{json.dumps({'isFinish': None, 'message': '正在处理数据库存储与短分享码...'})}\n"
                    code_hash = getStringHash(final_b64_string_data)
                    
                    db_op_success, db_result_hash, db_log_msgs = handle_database_storage(
                        code_hash, cleaned_db_root_name, None, 
                        final_b64_string_data, share_project_flag
                    )
                    for msg_item in db_log_msgs: 
                        yield f"{json.dumps({'isFinish': None, 'message': msg_item})}\n"
                    if db_op_success and db_result_hash:
                        short_share_code_result = db_result_hash 
                        yield f"{json.dumps({'isFinish': None, 'message': f'短分享码处理完成。短码为: {short_share_code_result}'})}\n"
                    else:
                        yield f"{json.dumps({'isFinish': None, 'message': '数据库操作未生成新的短分享码或按现有策略处理。长分享码仍然有效。'})}\n"
                
                response_payload_dict = {'longShareCode': final_b64_string_data}
                if short_share_code_result: 
                    response_payload_dict['shortShareCode'] = short_share_code_result
                final_success_message_json_str = json.dumps(response_payload_dict)
                yield f"{json.dumps({'isFinish': True, 'message': final_success_message_json_str})}\n"
            
            logger.info(f"导出任务 {task_id} 网盘操作部分完成。")

        except GeneratorExit: 
            logger.info(f"导出任务 {task_id} 客户端连接已断开 (GeneratorExit)。")
        except Exception as e:
            logger.error(f"API Export 主流程中发生错误 (任务 {task_id}): {e}", exc_info=True)
            try:
                yield f"{json.dumps({'isFinish': False, 'message': f'导出过程中服务器发生意外错误: {str(e)}'})}\n"
            except Exception as yield_err: 
                logger.warning(f"导出任务 {task_id}：向客户端发送错误信息时连接已断开: {yield_err}")
        finally:
            # finally 块总是会执行，无论 try 块如何退出（正常完成，return，break，异常）
            logger.debug(f"导出任务 {task_id}: 进入 finally 块。processed_by_queue={processed_by_queue}, login_success={login_success_flag}")
            if login_success_flag and driver: 
                try:
                    driver.doLogout()
                    logger.info(f"导出任务 {task_id}: 123网盘已注销。")
                except Exception as final_logout_err:
                    logger.error(f"导出任务 {task_id} 注销时发生错误: {final_logout_err}", exc_info=True)
            
            if processed_by_queue:
                 QUEUE_MANAGER.finish_processing(task_id)
                 # logger.info(f"导出任务 {task_id} 已完成，并从队列管理器移除。") # queue_manager内部有日志
            else:
                 # 如果任务在排队时客户端断开，processed_by_queue 会是 False
                 removed = QUEUE_MANAGER.remove_task_if_exists_and_not_processing(task_id)
                 # if removed: # queue_manager内部有日志
                 #     logger.info(f"导出任务 {task_id} 在排队时客户端断开或超时，已从等待队列中移除。")
                 # else:
                 #     logger.warning(f"导出任务 {task_id} 未开始处理，也未能从等待队列中移除（可能已被处理、超时或不存在）。")
            logger.info(f"Export stream finished for task {task_id}.")

    return Response(stream_with_context(generate_export_stream_with_queue()), mimetype='application/x-ndjson')