from flask import jsonify
from Pan123Database import Pan123Database
from loadSettings import loadSettings
from api.admin.admin_utils import admin_required
from getGlobalLogger import logger

DATABASE_PATH = loadSettings("DATABASE_PATH")

@admin_required
def handle_admin_update_database():
    """
    处理管理员更新数据库的请求。
    该函数会下载最新的数据库文件并将其导入到现有数据库中。
    """
    db = None
    try:
        logger.info("管理员后台：开始执行数据库更新流程...")
        db = Pan123Database(dbpath=DATABASE_PATH)

        logger.info("管理员后台：正在下载最新数据库...")
        # Pan123Database.downloadLatestDatabase() 方法会返回下载的文件路径
        latest_db_path = db.downloadLatestDatabase() # 注意这里的路径是下载后的临时路径
        logger.info(f"管理员后台：最新数据库已成功下载到 {latest_db_path}。")

        logger.info("管理员后台：正在将下载的数据库导入到主数据库...")
        # Pan123Database.importDatabase() 方法会处理导入逻辑，并在成功后删除临时文件
        db.importDatabase(latest_db_path) 
        # importDatabase 方法内部已经有日志记录，这里不再重复
        
        logger.info("管理员后台：数据库更新成功完成。")
        return jsonify({"isFinish": True, "message": "数据库已成功更新。"}), 200
    
    except Exception as e:
        # 记录详细的错误信息，包括堆栈跟踪
        logger.error(f"管理员后台：数据库更新过程中发生严重错误: {e}", exc_info=True)
        # 返回给前端一个用户友好的错误消息
        return jsonify({"isFinish": False, "message": f"数据库更新失败: {str(e)}"}), 500
    finally:
        if db:
            try:
                db.close()
                logger.info("管理员后台：数据库连接已关闭。")
            except Exception as e:
                logger.error(f"管理员后台：关闭数据库连接时出错: {e}", exc_info=True)
        logger.info("管理员后台：数据库更新流程结束。")