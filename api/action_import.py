import json
import time
import base64
from flask import Response, stream_with_context
from Pan123 import Pan123
from Pan123Database import Pan123Database
from utils import getStringHash, anonymizeId
from loadSettings import loadSettings
from api.api_utils import custom_secure_filename_part, handle_database_storage
from queueManager import QUEUE_MANAGER

from getGlobalLogger import logger

DATABASE_PATH = loadSettings("DATABASE_PATH")

def handle_import_request(data):
    username = data.get('username')
    password = data.get('password')
    code_hash_param = data.get('codeHash', None) 
    base64_data_param = data.get('base64Data', None) 
    root_folder_name_param = data.get('rootFolderName', None) 
    share_project_for_long_code = data.get('shareProject', False)
    filter_ids_param = data.get('filterIds', [])

    # 校验 filter_ids_param 是否为列表以及列表内元素是否为整数
    if not isinstance(filter_ids_param, list) or not all(isinstance(item, int) for item in filter_ids_param):
        logger.warning(f"导入请求中 filterIds 参数格式无效: {filter_ids_param}，将忽略此参数并导入全部。")
        filter_ids_param = [] # 如果格式不对，则重置为空列表，即导入全部

    if not username or not password:
        return Response(json.dumps({"isFinish": False, "message": "用户名和密码不能为空。"}),
                        mimetype='application/x-ndjson', status=400)
    is_short_code_import = bool(code_hash_param)
    is_long_code_import = bool(base64_data_param and root_folder_name_param)
    if not is_short_code_import and not is_long_code_import:
        return Response(json.dumps({"isFinish": False, "message": "导入参数不足：需要提供短分享码，或长分享码及根目录名。"}),
                        mimetype='application/x-ndjson', status=400)
    if is_short_code_import and is_long_code_import:
        return Response(json.dumps({"isFinish": False, "message": "导入参数冲突：短分享码与其他导入参数不能同时提供。"}),
                        mimetype='application/x-ndjson', status=400)

    cleaned_db_root_name_for_long_code = ""
    if is_long_code_import:
        cleaned_db_root_name_for_long_code = custom_secure_filename_part(root_folder_name_param)
        if share_project_for_long_code and not cleaned_db_root_name_for_long_code:
             return Response(json.dumps({"isFinish": False, "message": "使用长分享码加入资源共享计划时，必须填写有效的根目录名。"}),
                             mimetype='application/x-ndjson', status=400)
        elif not cleaned_db_root_name_for_long_code: # 如果不是共享计划，但根目录名清理后为空
            cleaned_db_root_name_for_long_code = f"导入的分享_{int(time.time())}"

    
    task_description_suffix = ""
    if filter_ids_param:
        task_description_suffix = f"_部分导入({len(filter_ids_param)}项)"

    task_description = f"导入_{username[:5]}..._{code_hash_param[:8] if code_hash_param else (root_folder_name_param[:10] if root_folder_name_param else '长码')}{task_description_suffix}"
    task_id = QUEUE_MANAGER.add_task(task_name=task_description)

    def generate_import_stream_with_queue():
        initial_greeting_sent = False
        processed_by_queue = False
        login_success_flag = False
        driver = None
        db_for_read_only = None

        try:
            log_msg_filter_ids = ""
            if filter_ids_param:
                log_msg_filter_ids = f" (Filter IDs: {str(filter_ids_param)[:100]}{'...' if len(str(filter_ids_param)) > 100 else ''})" # 避免日志过长
            else:
                log_msg_filter_ids = " (导入全部内容)"
            logger.info(f"导入任务 {task_id}: 开始排队/处理流程{log_msg_filter_ids}。")
            
            # 阶段1: 排队等待
            while not processed_by_queue:
                position, is_another_processing = QUEUE_MANAGER.get_task_position_and_is_processing_another(task_id)
                logger.debug(f"导入任务 {task_id}: 队列检查 - 位置 {position}, 其他处理中: {is_another_processing}")
                if position == -2:
                    yield f"{json.dumps({'isFinish': False, 'message': '任务ID无效、已过期或已被取消，请重试。'})}\n"
                    logger.warning(f"导入任务 {task_id} 在队列中未找到或已失效。")
                    return
                if position == 0 and not is_another_processing:
                    if not initial_greeting_sent:
                        yield f"{json.dumps({'isFinish': None, 'message': '恭喜! 哥们运气真好, 前面竟然 0 人排队! 小小后端, 快给这位爷伺候起来，优先服务!'})}\n"
                        initial_greeting_sent = True
                    if QUEUE_MANAGER.attempt_to_start_processing(task_id):
                        yield f"{json.dumps({'isFinish': None, 'message': '恭喜义父, 轮到您嘞! 操作即将开始...'})}\n"
                        processed_by_queue = True
                        break
                    else:
                        logger.warning(f"导入任务 {task_id}: 在队首但 attempt_to_start_processing 失败。")
                        yield f"{json.dumps({'isFinish': None, 'message': '系统正忙或任务状态变更，仍在尝试获取执行权...'})}\n"
                elif position >= 0:
                    people_ahead = position
                    yield f"{json.dumps({'isFinish': None, 'message': f'正在排队中... 前面还有 {people_ahead} 人。'})}\n"
                    initial_greeting_sent = True 
                else:
                    yield f"{json.dumps({'isFinish': False, 'message': f'未知的队列状态 ({position})，请重试。'})}\n"
                    logger.error(f"导入任务 {task_id} 遇到非预期的队列状态 {position}。")
                    return
                if not processed_by_queue:
                    time.sleep(5)

            # 阶段2: 实际操作
            if not processed_by_queue:
                logger.warning(f"任务 {task_id} (导入) 退出排队循环但 processed_by_queue 仍为 false，任务不执行。")
                return

            driver = Pan123()
            actual_base64_data_to_import = None
            actual_root_folder_name_to_import = None

            yield f"{json.dumps({'isFinish': None, 'message': '准备登录到123网盘...'})}\n"
            login_success_flag = driver.doLogin(username=username, password=password)
            if not login_success_flag:
                yield f"{json.dumps({'isFinish': False, 'message': '登录123网盘失败，请检查用户名和密码。'})}\n"
                return
            yield f"{json.dumps({'isFinish': None, 'message': '登录成功，准备导入数据...'})}\n"
            if filter_ids_param:
                yield f"{json.dumps({'isFinish': None, 'message': f'检测到部分文件导入模式，将导入 {len(filter_ids_param)} 个指定的文件。'})}\n"

            if is_short_code_import: 
                yield f"{json.dumps({'isFinish': None, 'message': f'正在通过短分享码 {code_hash_param[:8]}... 从数据库获取数据...'})}\n"
                db_for_read_only = Pan123Database(dbpath=DATABASE_PATH)
                share_data_list = db_for_read_only.getDataByHash(code_hash_param) 
                if not share_data_list or len(share_data_list) == 0:
                    yield f"{json.dumps({'isFinish': False, 'message': '短分享码无效或未在数据库中找到。'})}\n"
                    return
                actual_root_folder_name_to_import, actual_base64_data_to_import, _ = share_data_list[0]
                yield f"{json.dumps({'isFinish': None, 'message': f'从数据库获取数据成功，将导入为：{actual_root_folder_name_to_import}'})}\n"
            elif is_long_code_import: 
                actual_base64_data_to_import = base64_data_param
                actual_root_folder_name_to_import = cleaned_db_root_name_for_long_code
                yield f"{json.dumps({'isFinish': None, 'message': f'准备使用长分享码导入，根目录名：{actual_root_folder_name_to_import}'})}\n"
                if share_project_for_long_code: 
                    yield f"{json.dumps({'isFinish': None, 'message': '已勾选加入资源共享计划，正在将此长分享码存入数据库...'})}\n"
                    yield f"{json.dumps({'isFinish': None,'message': '数据匿名化...'})}\n"
                    
                    # 对长码数据进行匿名化处理
                    try:
                        decoded_data_for_anonymize = json.loads(base64.urlsafe_b64decode(actual_base64_data_to_import).decode("utf-8"))
                        anonymized_data_for_db = anonymizeId(decoded_data_for_anonymize)
                        b64_for_db_storage = base64.urlsafe_b64encode(json.dumps(anonymized_data_for_db, ensure_ascii=False).encode("utf-8")).decode("utf-8")
                    except Exception as e_anon:
                        logger.error(f"长码导入时匿名化失败: {e_anon}", exc_info=True)
                        yield f"{json.dumps({'isFinish': False, 'message': f'数据匿名化处理失败: {e_anon}。无法加入共享计划。'})}\n"
                        share_project_for_long_code = False # 由于匿名化失败，取消加入共享计划

                    yield f"{json.dumps({'isFinish': None,'message': '数据匿名化完成。'})}\n"

                    if share_project_for_long_code: # 再次检查，如果匿名化成功才执行
                        new_code_hash = getStringHash(b64_for_db_storage)
                        db_op_success, db_result_hash, db_log_msgs = handle_database_storage(
                            new_code_hash, actual_root_folder_name_to_import, None, 
                            b64_for_db_storage, is_share_project_request = True
                        )
                        for msg_item in db_log_msgs:
                            yield f"{json.dumps({'isFinish': None, 'message': msg_item})}\n"
                        if db_op_success and db_result_hash:
                            yield f"{json.dumps({'isFinish': None, 'message': f'此长分享码已存入数据库，对应短码为: {db_result_hash}'})}\n"
                        else:
                            yield f"{json.dumps({'isFinish': None, 'message': '将此长分享码存入数据库失败或记录已按策略处理。导入仍将继续。'})}\n"
            
            if not actual_base64_data_to_import or not actual_root_folder_name_to_import:
                yield f"{json.dumps({'isFinish': False, 'message': '内部错误：未能准备好导入所需的数据。'})}\n"
                return

            pan123_import_op_successful = False
            final_pan123_message = "123网盘导入操作未正常完成。"
            
            # 将 filter_ids_param 传递给 importFiles 函数
            for state in driver.importFiles(
                base64Data=actual_base64_data_to_import, 
                rootFolderName=actual_root_folder_name_to_import,
                filterIds=filter_ids_param # 传递 filterIds
                ):
                logger.debug(f"任务 {task_id} importFiles state: {json.dumps(state, ensure_ascii=False)}")
                if state.get("isFinish") is True:
                    pan123_import_op_successful = True
                    final_pan123_message = state["message"]
                    break 
                elif state.get("isFinish") is False:
                    final_pan123_message = state["message"]
                    yield f"{json.dumps(state)}\n" 
                    pan123_import_op_successful = False # 确保设置为False
                    # 不要在这里 return，让循环结束，或者直接 break
                    break # 如果操作失败，直接跳出循环
                else: # isFinish is None (进度更新)
                    yield f"{json.dumps(state)}\n"

            # 循环结束后，根据 pan123_import_op_successful 判断最终状态
            if not pan123_import_op_successful:
                 # 避免重复发送错误消息，如果上面已经发送了具体的失败消息
                if not final_pan123_message.startswith("123网盘导入操作未正常完成。"): # 如果不是默认消息
                    yield f"{json.dumps({'isFinish': False, 'message': final_pan123_message})}\n" 
                else: # 如果是默认消息，说明是意外中断
                    yield f"{json.dumps({'isFinish': False, 'message': '123网盘导入操作未成功完成或提前中止。'})}\n"
                return # 明确返回

            yield f"{json.dumps({'isFinish': True, 'message': final_pan123_message})}\n" 
            logger.info(f"导入任务 {task_id} 网盘操作部分完成。")

        except GeneratorExit: 
            logger.info(f"导入任务 {task_id} 客户端连接已断开 (GeneratorExit)。")
        except Exception as e:
            logger.error(f"API Import 主流程中发生错误 (任务 {task_id}): {e}", exc_info=True)
            try:
                yield f"{json.dumps({'isFinish': False, 'message': f'导入过程中服务器发生意外错误: {str(e)}'})}\n"
            except Exception as yield_err: 
                logger.warning(f"导入任务 {task_id}：向客户端发送错误信息时连接已断开: {yield_err}")
        finally:
            logger.debug(f"导入任务 {task_id}: 进入 finally 块。processed_by_queue={processed_by_queue}, login_success={login_success_flag}")
            if db_for_read_only:
                try:
                    db_for_read_only.close()
                except Exception as db_close_err:
                     logger.error(f"关闭只读数据库连接时出错: {db_close_err}", exc_info=True)

            if login_success_flag and driver:
                try:
                    driver.doLogout()
                    logger.info(f"导入任务 {task_id}: 123网盘已注销。")
                except Exception as final_logout_err:
                    logger.error(f"导入任务 {task_id} 注销时发生错误: {final_logout_err}", exc_info=True)
            
            if processed_by_queue: # 如果任务成功获取了处理权
                QUEUE_MANAGER.finish_processing(task_id)
            else: # 如果任务在排队时客户端断开或超时
                removed = QUEUE_MANAGER.remove_task_if_exists_and_not_processing(task_id)
                # 移除日志已在 queueManager 内部处理
            logger.info(f"Import stream finished for task {task_id}.")
                
    return Response(stream_with_context(generate_import_stream_with_queue()), mimetype='application/x-ndjson')