import logging
import logging.handlers
import os
import gzip
import shutil
from pathlib import Path
from datetime import datetime


# 创建日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
LOGGER_NAME = "app"
LOG_FORMAT = "%(levelprefix)s | %(asctime)s | %(message)s"
DETAILED_LOG_FORMAT = (
    "%(levelprefix)s | %(asctime)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)
LOG_LEVEL = "INFO"


def get_logger() -> logging.Logger:
    """
    获取配置好的日志记录器
    """
    return logging.getLogger(LOGGER_NAME)


class CompressedTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    带压缩功能的定时轮转日志处理器
    """

    def __init__(
        self,
        filename,
        when="h",
        interval=1,
        backupCount=0,
        encoding=None,
        delay=False,
        utc=False,
        atTime=None,
        suffix=None,
    ):
        """
        初始化处理器

        Args:
            filename: 日志文件名
            when: 轮转间隔的单位
            interval: 轮转的间隔数
            backupCount: 保留的备份数量
            encoding: 文件编码
            delay: 是否延迟创建文件
            utc: 是否使用UTC时间
            atTime: 在一天中的特定时间轮转
            suffix: 日志文件后缀格式，在标准TimedRotatingFileHandler中不支持，这里保存为实例变量
        """
        # 先调用父类初始化
        super().__init__(
            filename, when, interval, backupCount, encoding, delay, utc, atTime
        )
        # 设置后缀格式
        self.suffix = suffix if suffix else "%Y-%m-%d"

    def doRollover(self):
        """
        执行日志轮转并压缩旧日志文件
        """
        # 先执行父类的轮转操作
        super().doRollover()

        # 获取刚刚轮转的日志文件名
        if self.backupCount > 0:
            # 获取当前日期格式的后缀
            current_time = datetime.now()
            dfn = self.rotation_filename(
                self.baseFilename + "." + current_time.strftime(self.suffix)
            )

            # 检查文件是否存在且未压缩
            if os.path.exists(dfn) and not dfn.endswith(".gz"):
                # 压缩文件
                target_file = f"{dfn}.gz"
                with open(dfn, "rb") as f_in:
                    with gzip.open(target_file, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                # 删除原始文件
                os.remove(dfn)

            # 检查并压缩其他可能存在的旧日志文件
            dir_name, base_name = os.path.split(self.baseFilename)
            for file_name in os.listdir(dir_name):
                if (
                    file_name.startswith(base_name)
                    and file_name != base_name
                    and not file_name.endswith(".gz")
                ):
                    full_path = os.path.join(dir_name, file_name)
                    if os.path.isfile(full_path):
                        target_file = f"{full_path}.gz"
                        if not os.path.exists(target_file):
                            with open(full_path, "rb") as f_in:
                                with gzip.open(target_file, "wb") as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            # 删除原始文件
                            os.remove(full_path)


# 日志配置字典
log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": DETAILED_LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": "%(levelprefix)s | %(asctime)s | %(client_addr)s | %(request_line)s | %(status_code)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "detailed": {
            "formatter": "detailed",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "detailed",
            "class": "loggings.CompressedTimedRotatingFileHandler",
            "filename": str(LOG_DIR / "app.log"),
            "when": "midnight",  # 每天午夜轮转
            "interval": 1,  # 每1天轮转一次
            "backupCount": 30,  # 保留30天的日志
            "encoding": "utf8",
            "suffix": "%Y-%m-%d",  # 日志文件后缀格式
        },
        "error_file": {
            "formatter": "detailed",
            "class": "loggings.CompressedTimedRotatingFileHandler",
            "filename": str(LOG_DIR / "error.log"),
            "when": "midnight",  # 每天午夜轮转
            "interval": 1,  # 每1天轮转一次
            "backupCount": 30,  # 保留30天的日志
            "encoding": "utf8",
            "level": "ERROR",
            "suffix": "%Y-%m-%d",  # 日志文件后缀格式
        },
        "access_file": {
            "formatter": "access",
            "class": "loggings.CompressedTimedRotatingFileHandler",
            "filename": str(LOG_DIR / "access.log"),
            "when": "midnight",  # 每天午夜轮转
            "interval": 1,  # 每1天轮转一次
            "backupCount": 30,  # 保留30天的日志
            "encoding": "utf8",
            "suffix": "%Y-%m-%d",  # 日志文件后缀格式
        },
    },
    "loggers": {
        LOGGER_NAME: {
            "handlers": ["detailed", "file", "error_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["default", "file"],
            "level": LOG_LEVEL,
        },
        "uvicorn.error": {
            "handlers": ["default", "error_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["access", "access_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
    # 添加根日志记录器配置
    "root": {
        "handlers": ["detailed", "file", "error_file"],
        "level": LOG_LEVEL,
    },
}
