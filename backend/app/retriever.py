"""检索层：中文分词 + BM25，返回与用户问题最相关的知识块。

DeepSeek 不提供 embedding 接口，这里用轻量本地方案（jieba + BM25），
无需下载模型、完全离线，适合"按症状关键词定位章节"的检索场景。
"""
import math
import re
from collections import Counter
from typing import Dict, List

import jieba

from . import config
from .knowledge import load_chunks

# 构建文档词频所需
_average = 0.0


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[Dict[str, str]] = []
        self.doc_tokens: List[List[str]] = []
        self.doc_freq: Counter = Counter()
        self.avgdl = 0.0

    def _tokenize(self, text: str) -> List[str]:
        # 保留中文词 + 英文/数字 token，统一小写
        tokens = jieba.lcut(text)
        return [t.lower() for t in tokens if re.search(r"[\u4e00-\u9fffA-Za-z0-9]", t)]

    def build(self, documents: List[Dict[str, str]]):
        self.documents = documents
        self.doc_tokens = [self._tokenize(d["text"]) for d in documents]
        for toks in self.doc_tokens:
            for t in set(toks):
                self.doc_freq[t] += 1
        self.avgdl = sum(len(t) for t in self.doc_tokens) / max(1, len(self.doc_tokens))

    def search(self, query: str, top_k: int = None) -> List[Dict]:
        top_k = top_k or config.TOP_K
        if not self.documents:
            return []
        q_tokens = self._tokenize(query)
        qf = Counter(q_tokens)
        n = len(self.documents)
        scores = []
        for idx, toks in enumerate(self.doc_tokens):
            tf = Counter(toks)
            score = 0.0
            for term, qcnt in qf.items():
                df = self.doc_freq.get(term, 0)
                if df == 0:
                    continue
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
                tfc = tf.get(term, 0)
                denom = tfc + self.k1 * (1 - self.b + self.b * len(toks) / self.avgdl)
                score += qcnt * idf * tfc * (self.k1 + 1) / denom
            scores.append((score, idx))
        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, idx in scores:
            if score <= 0:
                continue
            results.append(
                {"id": self.documents[idx]["id"], "text": self.documents[idx]["text"], "score": round(score, 3)}
            )
            if len(results) >= top_k:
                break
        return results


_index: BM25Index = None


def get_index() -> BM25Index:
    global _index
    if _index is None:
        _index = BM25Index()
        _index.build(load_chunks())
    return _index


def retrieve(query: str, top_k: int = None) -> List[Dict]:
    return get_index().search(query, top_k)


if __name__ == "__main__":
    for q in ["电脑黑屏风扇在转", "游戏闪退", "鼠标卡顿", "连不上网"]:
        print(f"查询: {q}")
        for r in retrieve(q, 3):
            print(f"  [{r['id']}] {r['score']} {r['text'][:60]}...")
        print()