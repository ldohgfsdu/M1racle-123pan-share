# api/action_transform.py
import json
import base64
from flask import jsonify, request
from utils import transformShareCodeTo123FastLinkJson, transform123FastLinkJsonToShareCode, getStringHash
from api.api_utils import handle_database_storage
from getGlobalLogger import logger

def handle_transform_to_123fastlink_json_request():
    data = request.get_json()
    if not data:
        return jsonify({"isFinish": False, "message": "错误的请求：没有提供JSON数据。"}), 400

    share_code = data.get('shareCode')
    root_folder_name = data.get('rootFolderName')

    if not share_code or not isinstance(share_code, str) or not share_code.strip():
        return jsonify({"isFinish": False, "message": "错误的请求：'shareCode' 不能为空且必须是字符串。"}), 400
    if not root_folder_name or not isinstance(root_folder_name, str) or not root_folder_name.strip():
        return jsonify({"isFinish": False, "message": "错误的请求：'rootFolderName' 不能为空且必须是字符串，它将用作123FastLink的commonPath。"}), 400

    try:
        fastlink_json_output = transformShareCodeTo123FastLinkJson(root_folder_name, share_code)
        return jsonify({"isFinish": True, "message": fastlink_json_output}), 200
    except json.JSONDecodeError as e:
        logger.error(f"转换到123FastLink JSON时解码shareCode失败: {e}", exc_info=True)
        return jsonify({"isFinish": False, "message": f"无法解析提供的shareCode (可能不是有效的Base64编码的JSON): {str(e)}"}), 400
    except Exception as e:
        logger.error(f"转换到123FastLink JSON时发生错误: {e}", exc_info=True)
        return jsonify({"isFinish": False, "message": f"转换过程中发生错误: {str(e)}"}), 500

def handle_transform_from_123fastlink_json_request():
    # 如果 generateShortCode 为 True，则会将生成的 shareCode 存入数据库。
    # 如果同时 shareProject 为 True，则 visibleFlag 为 None (待审核)。
    # 如果 generateShortCode 为 True 但 shareProject 为 False，则 visibleFlag 为 False (私密)。
    data = request.get_json()
    if not data:
        return jsonify({"isFinish": False, "message": "错误的请求：没有提供JSON数据。"}), 400

    fastlink_json_str = data.get('123FastLinkJson')
    # 新增接收 generateShortCode 参数
    generate_short_code = data.get('generateShortCode', False) # 默认为False
    share_project = data.get('shareProject', False) # 默认为False

    if not fastlink_json_str or not isinstance(fastlink_json_str, str) or not fastlink_json_str.strip():
        return jsonify({"isFinish": False, "message": "错误的请求：'123FastLinkJson' 不能为空且必须是字符串。"}), 400
    if not isinstance(generate_short_code, bool):
        return jsonify({"isFinish": False, "message": "错误的请求：'generateShortCode' 必须是布尔值。"}), 400
    if not isinstance(share_project, bool):
        return jsonify({"isFinish": False, "message": "错误的请求：'shareProject' 必须是布尔值。"}), 400
    
    # 逻辑校验：如果 shareProject 为 true，则 generateShortCode 必须也为 true
    if share_project and not generate_short_code:
        # 理论上前端JS应该保证这一点，但后端也做校验以防万一
        logger.warning("API警告：收到 shareProject=True 但 generateShortCode=False 的请求，将强制 generateShortCode=True。")
        generate_short_code = True

    try:
        fastlink_json_dict = json.loads(fastlink_json_str)
    except json.JSONDecodeError as e:
        logger.error(f"从123FastLink JSON转换时解析输入JSON失败: {e}", exc_info=True)
        return jsonify({"isFinish": False, "message": f"无法解析提供的123FastLinkJson (它应该是一个JSON字符串): {str(e)}"}), 400

    try:
        transformed_data_list = transform123FastLinkJsonToShareCode(fastlink_json_dict)
        
        results_with_short_codes = []

        if not transformed_data_list:
             return jsonify({"isFinish": True, "message": [], "note": "转换成功，但没有生成任何分享码（可能是因为输入的123FastLink JSON为空或不包含文件）。"}), 200

        for item in transformed_data_list:
            current_root_name = item['rootFolderName']
            current_long_share_code = item['shareCode']
            current_short_share_code = None

            if generate_short_code: # 只有当用户希望生成短码时才进行数据库操作
                code_hash = getStringHash(current_long_share_code)
                
                # 根据 share_project 决定 visible_flag 的值
                # is_share_project_request 参数也传递给 handle_database_storage
                is_public_submission = share_project 
                
                op_success, result_hash, log_msgs = handle_database_storage(
                    code_hash,
                    current_root_name,
                    None, # visible_flag 会由 handle_database_storage 根据 is_public_submission 决定
                          # 如果 is_public_submission=True, 最终 visible_flag 是 None (待审核)
                          # 如果 is_public_submission=False, 最终 visible_flag 是 False (私密)
                          # （这里假设 handle_database_storage 内部逻辑是这样，需要确认或调整）
                          # 或者更明确地：
                          # db_visible_flag = None if is_public_submission else False
                    current_long_share_code,
                    is_public_submission 
                )
                
                for msg in log_msgs:
                    logger.info(f"[Transform API - DB Log for {current_root_name}]: {msg}")

                if op_success and result_hash:
                    current_short_share_code = result_hash
                elif not op_success:
                    logger.error(f"为 {current_root_name} 生成和存储短码失败。将只提供长码。")
            
            results_with_short_codes.append({
                "rootFolderName": current_root_name,
                "longShareCode": current_long_share_code,
                "shortShareCode": current_short_share_code
            })

        return jsonify({"isFinish": True, "message": results_with_short_codes}), 200
        
    except Exception as e:
        logger.error(f"从123FastLink JSON转换时发生错误: {e}", exc_info=True)
        return jsonify({"isFinish": False, "message": f"转换过程中发生错误: {str(e)}"}), 500