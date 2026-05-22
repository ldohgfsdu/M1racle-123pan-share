from flask import jsonify, request
from Pan123Database import Pan123Database
from loadSettings import loadSettings

from getGlobalLogger import logger

DATABASE_PATH = loadSettings("DATABASE_PATH")

def handle_get_sharecode():
    data = request.get_json()
    if not data or 'codeHash' not in data:
        return jsonify({"isFinish": False, "message": "错误的请求：必须提供 'codeHash'。"}), 400

    code_hash = data.get('codeHash')
    if not isinstance(code_hash, str) or not code_hash.strip() or len(code_hash) != 64:
        return jsonify({"isFinish": False, "message": "错误的请求：'codeHash' 必须是有效的字符串且不能为空。"}), 400

    db = None
    try:
        db = Pan123Database(dbpath=DATABASE_PATH)
        # Pan123Database.getDataByHash 返回一个列表，每个元素是 (rootFolderName, shareCode, visibleFlag)
        # 或者在没有找到时返回 None (在我们的实现中，是返回空列表，需要根据具体实现调整)
        # 假设 Pan123Database.getDataByHash(code_hash) 返回 [(rfn, sc, vf)] 或 []
        
        query_result = db.getDataByHash(code_hash) # 这应该返回一个列表
        
        if query_result and len(query_result) > 0:
            # 我们期望只有一个匹配项，取第一个
            # 元组解包 (rootFolderName, shareCode_from_db, visibleFlag)
            _, share_code_from_db, _ = query_result[0] 
            return jsonify({"isFinish": True, "message": share_code_from_db}), 200
        else:
            return jsonify({"isFinish": False, "message": f"未找到与提供的短分享码 {code_hash[:8]}... 对应的分享内容。"}), 404
            
    except Exception as e:
        logger.error(f"查询数据库时出错 (get_sharecode API): {e}", exc_info=True)
        return jsonify({"isFinish": False, "message": f"服务器内部错误，无法获取分享码: {str(e)}"}), 500
    finally:
        if db:
            db.close()