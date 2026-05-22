from flask import jsonify, request
from Pan123Database import Pan123Database
from loadSettings import loadSettings

from getGlobalLogger import logger

DATABASE_PATH = loadSettings("DATABASE_PATH")

def handle_search_database():
    """
    处理搜索数据库的API请求。
    传入JSON: {"rootFolderName": "搜索词", "page": 页码}
    返回JSON: {"success": bool, "files": [], "end": bool}
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "错误的请求：没有提供JSON数据。", "files": [], "end": True}), 400

    search_term = data.get('rootFolderName', '').strip()
    try:
        page = int(data.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    
    if not search_term: # 如果搜索词为空，可以视作返回空结果或提示需要搜索词
        return jsonify({"success": True, "files": [], "end": True, "message": "请输入搜索关键词。"}), 200

    db = None
    try:
        db = Pan123Database(dbpath=DATABASE_PATH)
        # 调用新的 searchDataByName 方法，它返回 (结果列表, 是否最后一页)
        shares_raw, is_end_page = db.searchDataByName(search_term, page)
        
        processed_shares = []
        # searchDataByName 返回的是 (codeHash, rootFolderName, timeStamp)
        for code_hash, name, ts in shares_raw:
            processed_shares.append({"name": name, "codeHash": code_hash, "timestamp": ts})
        
        return jsonify({"success": True, "files": processed_shares, "end": is_end_page}), 200

    except Exception as e:
        logger.error(f"搜索数据库时发生错误 (search_database API): {e}", exc_info=True)
        return jsonify({"success": False, "message": f"搜索时发生服务器错误: {str(e)}", "files": [], "end": True}), 500
    finally:
        if db:
            db.close()