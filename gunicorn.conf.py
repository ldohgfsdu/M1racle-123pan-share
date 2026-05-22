from loadSettings import loadSettings


# 服务器套接字配置
bind = f"0.0.0.0:{loadSettings('PORT')}"


# Worker进程配置，这里必须单进程运行
workers = 1
# Worker类型
# 'sync' 不支持多线程
# 'gevent' 或 'eventlet' 是异步IO worker
worker_class = 'gthread'
# 每个Worker进程的线程数
# 建议是 (2 * CPU核心数) + 1，或者根据IO密集程度调整，可以设置为CPU核心数的2到4倍
threads = 8
# 最大并发连接数
worker_connections = 1000


# 超时设置
# Worker处理请求的超时时间（秒）
timeout = 60
# HTTP Keep-Alive 连接的超时时间（秒）
keepalive = 5


# 进程管理
# 是否以守护进程方式运行 (通常在生产环境由systemd或supervisor管理，设为False)
daemon = False
# PID文件路径 (方便管理进程)
pidfile = 'gunicorn.pid'
# 进程名称
proc_name = 'pan123'


# 应用加载
# 在woker进程fork之前预加载应用代码
preload_app = True