import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from datetime import datetime
import getpass

class OneLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)

        # garante uma única linha
        msg = msg.replace("\n", " \\n ").replace("\r", " \\r ").replace("\t", " \\t ")
        
        return msg

def setup_logger(
    log_name: str = "AutonomousAgent",
    log_file: str = "agent.log",
    log_dir: str = "logs",
    level: int = logging.DEBUG,
):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)
    log_path_abs = os.path.abspath(log_path) 
    print(f"Log será salvo em: {os.path.abspath(log_path_abs)}")
    print(f"Log será salvo em: {os.path.abspath(log_path)}")

    logger = logging.getLogger(log_name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = OneLineFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("=" * 120)
    logger.info("Script iniciado")
    logger.info(f"Arquivo        : {os.path.basename(sys.argv[0])}")
    logger.info(f"Diretório      : {os.getcwd()}")
    logger.info(f"Usuário        : {getpass.getuser()}")
    logger.info(f"PID            : {os.getpid()}")
    logger.info(f"MOMENTO        : {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}")
    logger.info("=" * 120)

    return logger
