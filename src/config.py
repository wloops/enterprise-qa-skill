"""
配置加载模块
优先级：环境变量 > config.yaml > 默认值
"""
import os
from pathlib import Path
from typing import Optional


class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.db_path = ""
        self.kb_path = ""
        self.timezone = "Asia/Shanghai"
        self.kb_index_type = "bm25"  # bm25 | keyword
        self._load(config_path)

    def _load(self, config_path: Optional[str]):
        opts = _try_load_yaml(config_path)
        self.db_path = _first_of(
            os.environ.get("ENTERPRISE_QA_DB_PATH"),
            opts.get("database", {}).get("path"),
            _resolve_default("./enterprise.db"),
        )
        self.kb_path = _first_of(
            os.environ.get("ENTERPRISE_QA_KB_PATH"),
            opts.get("knowledge_base", {}).get("root_path"),
            _resolve_default("./knowledge"),
        )
        kb_cfg = opts.get("knowledge_base", {})
        self.kb_index_type = _first_of(
            kb_cfg.get("index_type"),
            "bm25"
        )
        self.timezone = _first_of(
            os.environ.get("TZ"),
            opts.get("timezone"),
            "Asia/Shanghai",
        )


def _try_load_yaml(config_path: Optional[str]) -> dict:
    search_paths = [config_path, "./config.yaml", "../config.yaml"]
    for p in search_paths:
        if p and Path(p).exists():
            try:
                import yaml
                with open(p, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
    return {}


def _first_of(*args):
    for v in args:
        if v is not None and v != "":
            return str(v)
    return ""


def _resolve_default(path: str) -> str:
    here = Path(__file__).resolve().parent.parent
    return str(here / path.lstrip("./"))


config = Config()
