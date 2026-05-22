from flask import jsonify, request
from Pan123Database import Pan123Database
from loadSettings import loadSettings

from getGlobalLogger import logger

DATABASE_PATH = loadSettings("DATABASE_PATH")

def handle_list_public_shares():
    db = None
    try:
        page = request.args.get('page', 1, type=int)
        if page < 1:
            page = 1

        db = Pan123Database(dbpath=DATABASE_PATH)
        # listData 现在返回 (结果列表, 是否最后一页)
        public_shares_raw, is_end_page = db.listData(visibleFlag=True, page=page) 
        
        processed_shares = []
        # listData 返回的是 (codeHash, rootFolderName, timeStamp)
        for code_hash, name, ts in public_shares_raw:
            processed_shares.append({"name": name, "codeHash": code_hash, "timestamp": ts})
        
        return jsonify({"success": True, "files": processed_shares, "end": is_end_page}), 200

    except Exception as e:
        logger.error(f"获取公共分享列表时出错 (list_public_shares API): {e}", exc_info=True)
        # 出错时也返回 "end": True，避免前端无限加载
        return jsonify({"success": False, "message": f"获取公共分享列表失败: {str(e)}", "files": [], "end": True}), 500
    finally:
        if db:
            db.close()