import base64
import json
from flask import jsonify, request
from utils import getStringHash, anonymizeId
from loadSettings import loadSettings
from api.api_utils import custom_secure_filename_part, handle_database_storage 

from getGlobalLogger import logger

DATABASE_PATH = loadSettings("DATABASE_PATH")

def handle_submit_database():
    data = request.get_json()
    if not data:
        return jsonify({"isFinish": False, "message": "错误的请求：没有提供JSON数据。"}), 400

    root_folder_name_raw = data.get('rootFolderName')
    base64_data = data.get('base64Data')
    share_project_flag = data.get('shareProject', False)
    
    try:
        base64_data = json.loads(base64.urlsafe_b64decode(base64_data).decode("utf-8"))
        base64_data = anonymizeId(base64_data)
        base64_data = base64.urlsafe_b64encode(json.dumps(base64_data, ensure_ascii=False).encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"提交数据库时发生错误 (submit_database API): {e}", exc_info=True)
        return jsonify({"isFinish": False, "message": "错误的请求：无法解析或验证 base64 数据。"}), 400

    # 参数校验
    if not root_folder_name_raw or not isinstance(root_folder_name_raw, str) or not root_folder_name_raw.strip():
        return jsonify({"isFinish": False, "message": "错误的请求：'rootFolderName' 不能为空且必须是字符串。"}), 400
    if not base64_data or not isinstance(base64_data, str) or not base64_data.strip():
        return jsonify({"isFinish": False, "message": "错误的请求：'base64Data' 不能为空且必须是字符串。"}), 400
    if not isinstance(share_project_flag, bool):
        return jsonify({"isFinish": False, "message": "错误的请求：'shareProject' 必须是布尔值。"}), 400

    cleaned_db_root_name = custom_secure_filename_part(root_folder_name_raw)
    # 如果清理后为空，custom_secure_filename_part 会返回 "untitled_share_{timestamp}"

    code_hash = getStringHash(base64_data)
    
    # visible_flag 的确定逻辑已移入 handle_database_storage 的调用处或其内部，
    # 这里我们直接传递 share_project_flag 给它，让它决定
    
    try:
        # 调用 api_utils 中的 handle_database_storage
        # 它返回: (operation_successful: bool, result_code_hash: str|None, message_log: list[str])
        op_overall_success, result_hash, log_msgs = handle_database_storage(
            code_hash, 
            cleaned_db_root_name, 
            None, # visible_flag 的具体值由 handle_database_storage 根据 is_share_project_request 决定
            base64_data, 
            share_project_flag # is_share_project_request
        )
        
        for msg in log_msgs:
            logger.debug(f"[SubmitDB API Log]: {msg}")

        if op_overall_success and result_hash:
            # 只要操作被认为是成功的（例如，记录已存在且短码有效，或新记录已插入）
            # 并且我们得到了一个有效的短码 (result_hash)
            return jsonify({"isFinish": True, "message": result_hash}), 200
        else:
            # 提取一个合适的错误信息给用户
            # 如果 op_overall_success 为 False，说明有严重错误
            # 如果 result_hash 为 None 但 op_overall_success 为 True，说明可能只是一个警告或信息性日志
            user_error_message = "数据库操作失败。" # 默认错误
            if log_msgs:
                # 尝试从日志中找到更具体的错误
                err_log = next((log for log in log_msgs if "错误：" in log or "失败" in log), None)
                if err_log:
                    user_error_message = err_log
                else: # 如果没有明确的错误，取最后一条信息
                    user_error_message = log_msgs[-1]
            
            # isFinish=False 表示执行失败
            # 状态码可以使用409 (Conflict) 如果是关于重复的，或500如果是通用服务器错误
            status_code = 500 if not op_overall_success else 409 # 粗略判断
            if "无法将新分享存入数据库" in user_error_message: status_code = 500
            if "已存在" in user_error_message and op_overall_success: status_code = 200 # 虽然isFinish=False，但hash有效，返回200？这里按要求isFinish=False
                                                                                    # 严格按照要求：isFinish=True 只有成功插入或已存在且短码有效的情况
                                                                                    # isFinish=False 是其他情况，message是错误
            
            # 如果 op_overall_success 是 true 但 result_hash 是 None，说明是“软”失败，但短码未生成/验证
            # 此时也应该返回 isFinish=False
            if op_overall_success and not result_hash:
                return jsonify({"isFinish": False, "message": "数据库操作部分成功，但未能生成有效的短分享码。"}), 500

            return jsonify({"isFinish": False, "message": user_error_message}), status_code

    except Exception as e:
        logger.error(f"提交数据库时发生意外错误 (submit_database API): {e}", exc_info=True)
        return jsonify({"isFinish": False, "message": f"服务器内部错误: {str(e)}"}), 500