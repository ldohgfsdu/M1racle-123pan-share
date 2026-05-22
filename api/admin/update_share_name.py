from flask import jsonify, request
from Pan123Database import Pan123Database
from loadSettings import loadSettings
from api.api_utils import custom_secure_filename_part # 从共享工具导入
from api.admin.admin_utils import admin_required

from getGlobalLogger import logger

DATABASE_PATH = loadSettings("DATABASE_PATH")

@admin_required
def handle_admin_update_share_name():
    data = request.get_json()
    code_hash = data.get('codeHash')
    new_name_raw = data.get('newName', '').strip() # 获取原始新名称

    if not code_hash or not new_name_raw: # 新名称不能为空
        return jsonify({"success": False, "message": "缺少参数 codeHash 或 newName，或newName为空。"}), 400
    
    new_name_cleaned = custom_secure_filename_part(new_name_raw) # 清理名称
    if not new_name_cleaned: # 如果清理后为空 (例如输入只包含非法字符)
        return jsonify({"success": False, "message": "提供的名称无效或清理后为空。"}), 400

    db = None
    try:
        db = Pan123Database(dbpath=DATABASE_PATH)
        if db.updateRootFolderName(code_hash, new_name_cleaned):
            return jsonify({"success": True, "message": "分享名称更新成功。", "cleanedName": new_name_cleaned}), 200
        else:
            return jsonify({"success": False, "message": "名称更新失败，记录可能不存在或数据库错误。"}), 500
    except Exception as e:
        logger.error(f"Admin API Error updating share name: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"更新名称时发生服务器错误: {str(e)}"}), 500
    finally:
        if db:
            db.close()