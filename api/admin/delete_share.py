from flask import jsonify, request
from Pan123Database import Pan123Database
from loadSettings import loadSettings
from api.admin.admin_utils import admin_required

from getGlobalLogger import logger

DATABASE_PATH = loadSettings("DATABASE_PATH")

@admin_required
def handle_admin_delete_share():
    data = request.get_json()
    code_hash = data.get('codeHash')

    if not code_hash:
        return jsonify({"success": False, "message": "缺少参数 codeHash。"}), 400

    db = None
    try:
        db = Pan123Database(dbpath=DATABASE_PATH)
        if db.deleteData(code_hash): # deleteData 返回 True 如果删除成功
            return jsonify({"success": True, "message": "分享记录删除成功。"}), 200
        else:
            # deleteData 返回 False 如果记录不存在
            return jsonify({"success": False, "message": "记录删除失败，可能该记录不存在。"}), 404 # Not Found
    except Exception as e:
        logger.error(f"Admin API Error deleting share: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"删除记录时发生服务器错误: {str(e)}"}), 500
    finally:
        if db:
            db.close()