"""知识库检索模块测试"""
import json
import os
import sys

import pytest

from src.kb import KBSearcher


@pytest.fixture
def searcher(test_kb_dir):
    return KBSearcher(test_kb_dir)


def _search_data(searcher, query, top_k=5):
    result = json.loads(searcher.search(query, top_k))
    return result["data"], result["_source"]


class TestKBSearch:
    def test_search_annual_leave(self, searcher):
        """T03 — 年假怎么算"""
        rows, src = _search_data(searcher, "年假怎么算")
        assert len(rows) > 0
        top_text = rows[0]["text"]
        assert "5 天" in top_text or "5天" in top_text

    def test_search_late_rule(self, searcher):
        """T04 — 迟到几次扣钱"""
        rows, src = _search_data(searcher, "迟到几次扣钱")
        assert len(rows) > 0
        top_text = rows[0]["text"]
        assert "50 元" in top_text or "50元" in top_text

    def test_search_promotion(self, searcher):
        """T07 相关 — P5 晋升 P6 条件"""
        rows, src = _search_data(searcher, "P5 晋升 P6 条件")
        assert len(rows) > 0
        sources = [r["source"] for r in rows]
        assert "promotion_rules.md" in sources

    def test_search_no_match(self, searcher):
        """T12 — 无匹配内容"""
        rows, src = _search_data(searcher, "xyzabc123 怎么报销")
        assert isinstance(rows, list)

    def test_source_annotation(self, searcher):
        """来源标注检查"""
        rows, src = _search_data(searcher, "病假怎么申请")
        for r in rows:
            assert "source" in r
            assert "section" in r
        assert "知识库检索" in src

    def test_search_hr_policy(self, searcher):
        """HR 制度检索"""
        rows, src = _search_data(searcher, "迟到怎么罚")
        assert len(rows) > 0
        assert rows[0]["source"] == "hr_policies.md"

    def test_global_source(self, searcher):
        """全局 _source 字段存在"""
        _, src = _search_data(searcher, "病假")
        assert len(src) > 0

    def test_empty_query(self, searcher):
        """空查询"""
        result = json.loads(searcher.search(""))
        assert result["data"] == []

    def test_list_docs(self, searcher):
        result = json.loads(searcher.list_docs())
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0
        assert "_source" in result
