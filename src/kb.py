"""
知识库检索模块 — 文档索引 + BM25/关键词搜索
"""
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

from .config import config
from .logger import get_logger

_log = get_logger("kb")


def _wrap(data: list, source: str) -> str:
    return json.dumps({"data": data, "_source": source}, ensure_ascii=False)


def _now() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


class KBSearcher:
    """知识库搜索引擎"""

    def __init__(self, kb_path: Optional[str] = None):
        self.root = Path(kb_path or config.kb_path).resolve()
        self.index_type = config.kb_index_type  # bm25 | keyword
        self._docs: list[dict] = []  # [{"path": ..., "section": ..., "text": ..., "source": ...}]
        self._bm25: Optional[BM25Okapi] = None
        self._corpus: list[list[str]] = []
        self._build_index()

    def _build_index(self):
        """扫描知识库目录，建立索引"""
        if not self.root.exists():
            return

        for md_file in sorted(self.root.rglob("*.md")):
            rel_path = md_file.relative_to(self.root)
            doc_name = str(rel_path).replace("\\", "/")

            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue

            # 按 ## 标题分块
            sections = self._split_sections(content, doc_name)
            self._docs.extend(sections)

        # 构建 BM25 语料库
        self._corpus = [self._tokenize(d["text"]) for d in self._docs]
        if self._corpus:
            self._bm25 = BM25Okapi(self._corpus)

    def _split_sections(self, content: str, doc_name: str) -> list[dict]:
        """按 ## 标题分割文档段落"""
        sections = []
        # 用正则按 ## 标题分割，保留标题
        lines = content.split("\n")
        current_title = doc_name
        current_lines = []

        for line in lines:
            if re.match(r"^##\s+", line):
                # 保存上一段
                if current_lines:
                    text = "\n".join(current_lines).strip()
                    if text and len(text) > 10:
                        sections.append({
                            "source": doc_name,
                            "section": current_title,
                            "text": text,
                        })
                current_title = f"{doc_name} > {line.strip('# ').strip()}"
                current_lines = [line]
            else:
                current_lines.append(line)

        # 最后一段
        if current_lines:
            text = "\n".join(current_lines).strip()
            if text and len(text) > 10:
                sections.append({
                    "source": doc_name,
                    "section": current_title,
                    "text": text,
                })

        return sections

    def _tokenize(self, text: str) -> list[str]:
        """中文/英文分词 — unigram + overlapping bigram"""
        tokens = []
        # 提取所有英文单词和数字
        eng_tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
        tokens.extend(eng_tokens)
        # 提取中文连续块
        chinese = re.findall(r"[一-鿿㐀-䶿]+", text)
        for chunk in chinese:
            # 单字 token
            tokens.extend(chunk)
            # overlapping bigram
            for i in range(len(chunk) - 1):
                tokens.append(chunk[i:i+2])
        return tokens

    def search(self, query: str, top_k: int = 5) -> str:
        """搜索知识库，返回 {data, _source} 格式"""
        t0 = time.time()
        source_label = f"知识库检索 (查询: {query}, {_now()})"

        if not self._docs:
            _log.warning("search_kb: 知识库为空")
            return _wrap([], source_label)

        query_tokens = self._tokenize(query)
        if not query_tokens:
            _log.warning("search_kb: 查询词为空")
            return _wrap([], source_label)

        if self.index_type == "bm25" and self._bm25:
            scores = self._bm25.get_scores(query_tokens)
            ranked = sorted(
                enumerate(scores), key=lambda x: x[1], reverse=True
            )[:top_k]
            results = [
                {
                    "source": self._docs[i]["source"],
                    "section": self._docs[i]["section"],
                    "text": self._docs[i]["text"][:500],
                    "score": round(float(s), 4),
                }
                for i, s in ranked
                if s > 0
            ]
            if not results:
                results = self._keyword_search(query_tokens, top_k)
        else:
            # 关键词回退：统计每个文档的命中次数
            results = self._keyword_search(query_tokens, top_k)

        _log.info("search_kb(%s) -> %d results (%.1fms)", query, len(results), (time.time()-t0)*1000)
        return _wrap(results, source_label)

    def _keyword_search(self, query_tokens: list[str], top_k: int) -> list[dict]:
        """关键词匹配（回退方案）"""
        scored = []
        for idx, doc in enumerate(self._docs):
            text_lower = doc["text"].lower()
            score = sum(1 for t in query_tokens if t in text_lower)
            if score > 0:
                scored.append((idx, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "source": self._docs[i]["source"],
                "section": self._docs[i]["section"],
                "text": self._docs[i]["text"][:500],
                "score": float(s),
            }
            for i, s in scored[:top_k]
        ]

    def list_docs(self) -> str:
        """列出所有知识库文档"""
        _log.info("list_docs requested")
        doc_names = sorted(set(d["source"] for d in self._docs))
        return _wrap(doc_names, f"知识库文档清单 ({_now()})")


_searcher: Optional[KBSearcher] = None


def get_searcher() -> KBSearcher:
    global _searcher
    if _searcher is None:
        _searcher = KBSearcher()
    return _searcher


def search_kb(query: str, top_k: int = 5) -> str:
    """搜索知识库"""
    return get_searcher().search(query, top_k)


def list_docs() -> str:
    """列出所有文档"""
    return get_searcher().list_docs()
