import logging.config
from loggings import log_config

# 应用日志配置
logging.config.dictConfig(log_config)

# Gunicorn 配置
bind = "0.0.0.0:5000"
workers = 3
worker_class = "uvicorn.workers.UvicornWorker"

# 日志相关配置
loglevel = "info"
accesslog = "-"
errorlog = "-"

# 其他配置
preload_app = False
