from flask import jsonify, request
from Pan123Database import Pan123Database
from utils import generateContentTree
from loadSettings import loadSettings

from getGlobalLogger import logger

DATABASE_PATH = loadSettings("DATABASE_PATH")

def handle_get_content_tree():
    data = request.get_json()
    if not data:
        return jsonify({"isFinish": False, "message": "错误的请求：没有提供JSON数据。"}), 400

    code_hash = data.get('codeHash')
    share_code_b64_from_request = data.get('shareCode') # 用户可能直接提供长码
    
    target_share_code_for_tree = None
    db = None # 初始化数据库连接变量

    try:
        if code_hash: # 如果提供了短码，优先从数据库查找
            db = Pan123Database(dbpath=DATABASE_PATH)
            share_data_list = db.getDataByHash(code_hash) 
            if share_data_list and len(share_data_list) > 0:
                target_share_code_for_tree = share_data_list[0][1] # (rootFolderName, shareCode, visibleFlag) -> shareCode
            else:
                return jsonify({"isFinish": False, "message": f"错误：未找到与提供的短分享码 {code_hash[:8]}... 对应的分享内容。"}), 404
        elif share_code_b64_from_request: # 如果没有短码，但直接提供了长码
            target_share_code_for_tree = share_code_b64_from_request
        else: # 两个都没提供
            return jsonify({"isFinish": False, "message": "错误：必须提供 'codeHash' 或 'shareCode'。"}), 400

        if not target_share_code_for_tree:
            # 此情况理论上已被前述逻辑覆盖，但作为安全回退
            return jsonify({"isFinish": False, "message": "错误：未能获得有效的分享码以生成目录树。"}), 500
            
        # 调用 generateContentTree 函数
        # generateContentTree 返回 {"isFinish": True/False, "message": 结果列表或错误信息字符串}
        result_dict = generateContentTree(target_share_code_for_tree)
        return jsonify(result_dict) # 直接返回generateContentTree的结果

    except Exception as e:
        logger.error(f"调用 generateContentTree 或数据库查询时发生错误 (get_content_tree API): {e}", exc_info=True)
        return jsonify({"isFinish": False, "message": f"生成目录树时发生服务器内部错误: {str(e)}"}), 500
    finally:
        if db: # 确保关闭数据库连接
            db.close()