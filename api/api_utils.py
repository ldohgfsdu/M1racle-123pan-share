import re
import unicodedata
import time
from getGlobalLogger import logger

from Pan123Database import Pan123Database
from loadSettings import loadSettings

DATABASE_PATH = loadSettings("DATABASE_PATH")

def custom_secure_filename_part(name_str):
    """
    清理用户输入的文件名部分，移除路径相关和常见非法字符，但保留中文、字母、数字等。
    用于数据库中存储的 rootFolderName。
    """
    if not name_str:
        return ""
    
    name_str = unicodedata.normalize('NFC', name_str)
    # 移除所有控制字符 (Cc, Cf, Cs, Co, Cn)
    name_str = "".join(c for c in name_str if unicodedata.category(c)[0] != "C")
    # 替换常见非法文件名字符
    name_str = re.sub(r'[\\/:*?"<>|]', '_', name_str)
    # 移除开头和结尾的点和空格
    name_str = name_str.strip(' .')
    # 如果文件名完全由点号组成 (例如 "...")，替换为单个下划线
    if re.fullmatch(r'\.+', name_str): 
        return "_" 
    # 如果清理后为空，提供一个默认名（时间戳）
    if not name_str: 
        return f"untitled_share_{int(time.time())}"
    return name_str

def handle_database_storage(code_hash, root_folder_name_cleaned, visible_flag, share_code_b64, is_share_project_request):
    """
    处理数据存储到数据库的通用逻辑，包括覆写。
    返回元组: (operation_successful: bool, result_code_hash: str|None, message_log: list[str])
    
    visible_flag:
        None: 共享计划 - 待审核
        True: 共享计划 - 已通过 (通常由管理员设置)
        False: 私密短码
    is_share_project_request: 布尔值，指示当前请求是否明确要求加入共享计划。
                              如果为True，则visible_flag在插入时应为None。
    """
    db_instance = None #确保在finally中可以被访问
    operation_successful = False # 标记整体操作是否应被视为成功（例如，短码是否有效）
    final_result_code_hash = None # 最终返回的短码
    message_log = []

    try:
        db_instance = Pan123Database(dbpath=DATABASE_PATH)
        existing_entry = db_instance.getDataByHash(code_hash)

        # 逻辑
        # 现有可见性  新请求       操作                  最终数据库状态
        # False       True       删除旧的，插入新的      待审核(None)
        # None        True       更新名称               待审核(None)
        # True        True       不执行操作             公开(True)
        # False       False      更新名称               私密(False)
        # None        False      不执行操作             待审核(None)
        # True        False      不执行操作             公开(True)
        
        if existing_entry:
            message_log.append(f"数据库中已存在具有相同内容的分享 (Hash: {code_hash[:8]}...)。")
            existing_root_folder_name, _esc, existing_visible_flag = existing_entry[0]
            final_result_code_hash = code_hash # 已存在，短码有效

            if is_share_project_request and existing_visible_flag is False:
                # 情况: 现有的是私密(False)，新请求是加入共享计划(is_share_project_request=True, 对应visible_flag=None)
                # 操作: 删除旧的，插入新的 (待审核)
                message_log.append(f"检测到私密分享 (原名: {existing_root_folder_name}) 将升级为公共分享 (待审核，新名: {root_folder_name_cleaned})。")
                if db_instance.deleteData(code_hash):
                    message_log.append("原私密分享记录已成功删除。")
                    if db_instance.insertData(code_hash, root_folder_name_cleaned, None, share_code_b64):
                        operation_successful = True
                        message_log.append("成功将分享作为公共待审核项存入数据库。")
                    else:
                        operation_successful = False # 删除后插入失败，这是个问题
                        message_log.append("错误：删除旧私密分享后，无法重新插入为公共分享。")
                else:
                    operation_successful = False # 删除失败
                    message_log.append("错误：尝试删除旧私密分享记录失败。")

            elif existing_visible_flag is None and is_share_project_request:
                # 情况: 现有的是待审核(None)，新请求也是加入共享计划
                # 操作: 无需更改，短码有效。可以考虑更新时间戳或名称（如果不同）
                operation_successful = True
                message_log.append(f"此分享已作为待审核项 (名称: {existing_root_folder_name}) 存在于数据库中。短分享码有效。")
                if existing_root_folder_name != root_folder_name_cleaned :
                    if db_instance.updateRootFolderName(code_hash, root_folder_name_cleaned):
                        message_log.append(f"分享名称已更新为: {root_folder_name_cleaned}。")
                    else :
                        message_log.append(f"尝试更新分享名称为 {root_folder_name_cleaned} 失败。")

            elif existing_visible_flag is True and is_share_project_request:
                # 情况: 现有的是已通过的公共分享(True)，新请求是加入共享计划
                # 操作: 通常不应由用户降级或修改，提示已存在且公开。短码有效。
                operation_successful = True
                message_log.append(f"此分享已作为公共资源 (名称: {existing_root_folder_name}) 存在于数据库中。短分享码有效。")

            elif not is_share_project_request and existing_visible_flag is False:
                # 情况: 现有的是私密(False)，新请求也是私密(visible_flag传进来会是False)
                # 操作: 无需更改，短码有效。
                operation_successful = True
                message_log.append(f"此分享已作为私密短码 (名称: {existing_root_folder_name}) 存在。短分享码有效。")
                if existing_root_folder_name != root_folder_name_cleaned : # 如果用户提供了新的私密分享名称
                    if db_instance.updateRootFolderName(code_hash, root_folder_name_cleaned):
                        message_log.append(f"私密分享名称已更新为: {root_folder_name_cleaned}。")
                    else :
                        message_log.append(f"尝试更新私密分享名称为 {root_folder_name_cleaned} 失败。")

            else:
                # 其他复杂情况，例如：
                # 1. 现有是公共(True)，新请求是私密(False)
                # 2. 现有是待审核(None)，新请求是私密(False)
                # 当前策略是：不进行数据库修改。
                operation_successful = True
                message_log.append(f"数据库中已存在此分享 (名称: {existing_root_folder_name}, 状态: {existing_visible_flag})。")
                message_log.append("根据当前策略，未修改数据库记录。您可以使用现有短分享码。")

        else: # 数据库中不存在此 code_hash，进行全新插入
            final_visible_flag_for_insert = None if is_share_project_request else False # 新私密

            if db_instance.insertData(code_hash, root_folder_name_cleaned, final_visible_flag_for_insert, share_code_b64):
                operation_successful = True
                final_result_code_hash = code_hash
                status_desc = "公共待审核" if final_visible_flag_for_insert is None else "私密"
                message_log.append(f"成功将新分享作为 {status_desc} 项 (根目录名: {root_folder_name_cleaned}) 存入数据库。")
            else:
                operation_successful = False
                message_log.append("错误：无法将新分享存入数据库。")
                
    except Exception as e:
        operation_successful = False
        message_log.append(f"数据库操作时发生意外错误: {str(e)}")
        logger.error(f"数据库操作时发生意外错误: {str(e)}", exc_info=True)
    finally:
        if db_instance:
            db_instance.close()
            
    return operation_successful, final_result_code_hash, message_log