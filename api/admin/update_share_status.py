from flask import jsonify, request
from Pan123Database import Pan123Database
from loadSettings import loadSettings
from api.admin.admin_utils import admin_required

from getGlobalLogger import logger

DATABASE_PATH = loadSettings("DATABASE_PATH")

@admin_required
def handle_admin_update_share_status():
    data = request.get_json()
    code_hash = data.get('codeHash')
    new_status_str = data.get('newStatus') # 前端传来 "approved", "pending", "private"

    if not code_hash or new_status_str is None:
        return jsonify({"success": False, "message": "缺少参数 codeHash 或 newStatus。"}), 400

    # 将前端的状态字符串转换为数据库期望的 visibleFlag 值
    new_visible_flag_for_db = None # 默认为 None (对应 "pending")
    if new_status_str == "approved":
        new_visible_flag_for_db = True
    elif new_status_str == "private":
        new_visible_flag_for_db = False
    elif new_status_str == "pending":
        new_visible_flag_for_db = None # SQLite NULL
    else:
        return jsonify({"success": False, "message": "无效的状态值。"}), 400

    db = None
    try:
        db = Pan123Database(dbpath=DATABASE_PATH)
        if db.updateVisibleFlag(code_hash, new_visible_flag_for_db):
            return jsonify({"success": True, "message": "分享状态更新成功。"}), 200
        else:
            # updateVisibleFlag 返回 False 可能是因为记录未找到
            return jsonify({"success": False, "message": "状态更新失败，记录可能不存在或数据库内部错误。"}), 500 
    except Exception as e:
        logger.error(f"Admin API Error updating share status: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"更新状态时发生服务器错误: {str(e)}"}), 500
    finally:
        if db:
            db.close()