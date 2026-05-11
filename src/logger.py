"""日志系统 — 从 config.yaml 读取配置"""
import logging
import os
from pathlib import Path

from .config import config


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # 控制台 handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    # 文件 handler（如果配置了）
    try:
        log_file = config._opts.get("logging", {}).get("file", "") if hasattr(config, '_opts') else ""
    except Exception:
        log_file = ""

    if not log_file:
        # 尝试从 config.yaml 直接读
        try:
            import yaml
            cfg_path = Path(__file__).resolve().parent.parent / "config.yaml"
            if cfg_path.exists():
                with open(cfg_path, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                log_file = cfg.get("logging", {}).get("file", "")
        except Exception:
            pass

    if log_file:
        log_path = Path(log_file)
        if not log_path.is_absolute():
            log_path = Path(__file__).resolve().parent.parent / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(str(log_path), encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(fh)

    return logger
