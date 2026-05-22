import logging
import os
import time
from logging.handlers import RotatingFileHandler

from loadSettings import loadSettings

_logger_configured_flag = False
logger = logging.getLogger("123PanShareApp") # 使用自定义的应用名称, 避免与 root logger 冲突

def setup_logger():
    global logger, _logger_configured_flag

    # 防止重复配置 (如果此函数因某种原因被多次调用)
    if _logger_configured_flag:
        return logger

    # 从配置加载日志级别，如果失败则默认为 INFO
    log_level_str = loadSettings("LOGGING_LEVEL")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logger.setLevel(log_level)

    # 移除已存在的 handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 日志格式
    formatter = logging.Formatter(
        '[%(asctime)s.%(msecs)03d][%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 文件处理器
    log_dir = loadSettings("LOG_DIR")
    file_handler = None # 初始化为None，以便后续检查是否成功创建
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except OSError as e:
            print(f"[getGlobalLogger.py - ERROR] 无法创建日志目录 '{log_dir}': {e}。文件日志将不可用。")
    
    # 使用应用启动时的时间生成日志文件名
    # current_time_for_logfile = time.strftime('%Y-%m-%d-%H-%M-%S')
    current_time_for_logfile = time.strftime('%Y-%m-%d')
    log_filename = os.path.join(log_dir, f"{current_time_for_logfile}.log")
    try:
        # 每个文件 10MB
        file_handler = RotatingFileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(log_level) # 文件处理器遵循配置的日志级别
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # 如果文件处理器创建失败，则在控制台打印错误
        print(f"[getGlobalLogger.py - ERROR] 无法创建日志文件处理器 '{log_filename}': {e}。文件日志可能部分或完全不可用。")
        file_handler = None # 标记为失败

    # 控制台处理器
    console_handler = logging.StreamHandler() # 默认输出到 sys.stderr
    console_handler.setLevel(log_level) # 控制台处理器遵循配置的日志级别
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 检查是否至少有一个处理器被成功添加
    if not logger.handlers:
        # 这是一个极端情况，例如如果 StreamHandler 也因某种原因失败
        print("[getGlobalLogger.py - CRITICAL] 未能配置任何日志处理器。日志可能不会按预期工作。")
        basic_stderr_handler = logging.StreamHandler() # 直接到 stderr
        basic_stderr_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s')) # 极简格式
        logger.addHandler(basic_stderr_handler)
        logger.setLevel(logging.WARNING) # 至少警告级别应该能看到

    # 记录一条初始化信息，这条信息会同时输出到文件和控制台（如果都配置成功）
    init_message = f"全局日志系统初始化完成。应用日志级别: {log_level_str}"
    if file_handler and file_handler.baseFilename:
        init_message += f", 主日志文件: {os.path.abspath(file_handler.baseFilename)}"
    else:
        init_message += ", 文件日志记录失败或未启用"
    
    # logger.info(init_message) # logger.info 可能因为级别设置而不显示, 所以这里直接 print
    print(f"[getGlobalLogger.py - INFO] {init_message}")

    _logger_configured_flag = True # 标记为已配置
    return logger

# 在模块导入时就配置好 logger
setup_logger()