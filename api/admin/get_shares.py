from flask import jsonify, request
from Pan123Database import Pan123Database
from loadSettings import loadSettings
from api.admin.admin_utils import admin_required 

from getGlobalLogger import logger

DATABASE_PATH = loadSettings("DATABASE_PATH")

@admin_required
def handle_admin_get_shares():
    db = None
    try:
        status = request.args.get('status', type=str) # 'approved', 'pending', 'private'
        page = request.args.get('page', 1, type=int)
        if page < 1:
            page = 1

        if status not in ['approved', 'pending', 'private']:
            return jsonify({"success": False, "message": "无效的状态参数。", "shares": [], "end": True}), 400

        db = Pan123Database(dbpath=DATABASE_PATH)
        # 调用新的 getSharesByStatusPaged 方法
        # 它返回: (shares_list, is_end_page)
        # shares_list 内部元素是 (codeHash, rootFolderName, shareCode, timeStamp, visibleFlag_py)
        raw_shares_data, is_end_page = db.getSharesByStatusPaged(status_filter=status, page=page)
        
        processed_shares = []
        for code_hash, name, share_code, ts, visible_flag_py in raw_shares_data:
            item = {
                "codeHash": code_hash, 
                "rootFolderName": name, 
                "shareCode": share_code, 
                "timeStamp": ts, 
                "visibleFlag": visible_flag_py # 这是处理过的 Python bool 或 None
            }
            processed_shares.append(item)
        
        return jsonify({
            "success": True,
            "shares": processed_shares, # 当前页的分享数据
            "end": is_end_page         # 是否是最后一页
        }), 200

    except Exception as e:
        logger.error(f"管理后台获取分享列表时出错: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"获取分享列表失败: {str(e)}", "shares": [], "end": True}), 500
    finally:
        if db:
            db.close()