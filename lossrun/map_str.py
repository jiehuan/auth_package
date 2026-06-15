"""
Optimized _map_str_bbox / _build_doc_word_index

主要改动:
1. 用 rapidfuzz.partial_ratio_alignment 替代 regex 模糊匹配 (e<=5 + overlapped=True)
   - regex 模糊匹配是回溯式, 错误数>2 时在长文本上接近指数级慢
   - rapidfuzz 是 bit-parallel Levenshtein (C++), 一次扫描得到最优子串位置
2. 建索引时统一归一化 (casefold + NFKC + 引号/全角字符映射), pos/len 基于
   归一化后的文本计算, 因此偏移量天然一致, 匹配率显著提升
3. 先尝试 O(n) 的精确 substring 查找 (归一化后大部分能直接命中), 失败才走模糊匹配
4. page_pos / max_page 缓存在 di.attrs, 不再每次调用重建
5. 词选择用区间重叠判断 (而非 pos>=start), 不会丢掉匹配起点落在词中间的首词
6. 去掉 iterrows, 改向量化赋值

依赖: pip install rapidfuzz
"""

import json
import logging
import unicodedata

import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# 常见 OCR/LLM 文本差异: 弯引号、长短横线、全角标点、NBSP
_CHAR_MAP = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-",
    "\u00a0": " ",
    "\uff0c": ",", "\uff0e": ".", "\uff1a": ":", "\uff1b": ";",
    "\uff08": "(", "\uff09": ")", "\uff05": "%", "\uff04": "$",
})

FUZZY_SCORE_CUTOFF = 85  # 0-100, 越低越宽容; 可按数据调整


def _norm(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", str(text)).translate(_CHAR_MAP).casefold()


def _norm_query(s: str) -> str:
    # LLM 输出可能含换行/多空格; 索引侧是单空格 join, 这里折叠成同样形态
    return " ".join(_norm(s).split())


class WorkerPool:

    @staticmethod
    def _build_doc_word_index(doc_intel_json: str | None) -> pd.DataFrame | None:
        if not doc_intel_json:
            return None
        try:
            di = pd.json_normalize(json.loads(doc_intel_json))
        except Exception:
            logger.info("cannot load doc_intel_json")
            return None

        di = di.explode("words")
        w = di["words"]
        di["content"] = w.apply(lambda x: x.get("content") if isinstance(x, dict) else None)
        di["boundingBox"] = w.apply(lambda x: x.get("polygon") if isinstance(x, dict) else None)
        di = di.loc[~di["content"].isna() & ~di["boundingBox"].isna()]
        if di.empty:
            return None

        di = di[["content", "pageNumber", "boundingBox", "height", "width", "unit"]]
        bb = di["boundingBox"]
        di["x0"] = bb.apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)
        di["y0"] = bb.apply(lambda x: x[1] if isinstance(x, list) and len(x) > 1 else None)
        di["x1"] = bb.apply(lambda x: x[4] if isinstance(x, list) and len(x) > 4 else None)
        di["y1"] = bb.apply(lambda x: x[5] if isinstance(x, list) and len(x) > 5 else None)
        di = di.loc[~di["x0"].isna() & ~di["y0"].isna() & ~di["x1"].isna() & ~di["y1"].isna()]
        if di.empty:
            return None

        di = di.reset_index(drop=True)
        # 关键: 在索引侧归一化, pos/len 与匹配用的 doc_str 完全一致, 无需偏移换算
        di["content"] = di["content"].map(_norm)
        di["len"] = di["content"].str.len() + 1  # +1 = join 的空格
        di["pos"] = di["len"].cumsum().shift().fillna(0).astype(int)

        # 文档级常量只算一次 (mask 成 "|" 不改变 len/pos, 所以这两个缓存始终有效)
        di.attrs["page_pos"] = di.groupby("pageNumber")["pos"].min().to_dict()
        di.attrs["max_page"] = int(di["pageNumber"].max())
        return di

    @staticmethod
    def _map_str_bbox(s, di, page_start, n) -> tuple[pd.DataFrame, int | None, str | None]:
        if di is None or not s:
            return di, None, None

        s_norm = _norm_query(s)
        if not s_norm:
            return di, None, None

        if page_start is None:
            page_start = 1

        # doc_str 每次重建是必要的 (上一次匹配会把命中词 mask 成 "|"), 但 join 是 O(n), 不是瓶颈
        doc_str = " ".join(di["content"])
        page_pos = di.attrs.get("page_pos") or di.groupby("pageNumber")["pos"].min().to_dict()
        max_page = di.attrs.get("max_page") or int(di["pageNumber"].max())
        doc_end = len(doc_str)

        if page_start > max_page:
            start, end = 0, doc_end
        else:
            start = int(page_pos.get(page_start, 0))
            end_page = min(page_start + n, max_page)
            end = int(page_pos.get(end_page + 1, doc_end))

        def locate(w_start: int, w_end: int) -> tuple[int, int] | None:
            window = doc_str[w_start:w_end]
            # 1) 精确查找: 归一化后大多数 case 在这里 O(n) 直接命中
            i = window.find(s_norm)
            if i >= 0:
                return w_start + i, w_start + i + len(s_norm)
            # 2) 模糊对齐: 一次调用返回最优子串的位置与分数
            aln = fuzz.partial_ratio_alignment(s_norm, window,
                                               score_cutoff=FUZZY_SCORE_CUTOFF)
            if aln is None:
                return None
            return w_start + aln.dest_start, w_start + aln.dest_end

        span = locate(start, end)
        if span is None and (start > 0 or end < doc_end):
            span = locate(0, doc_end)  # 窗口内没找到, 退回全文
        if span is None:
            return di, None, None

        abs_start, abs_end = span
        word_end = di["pos"] + di["len"] - 1  # 词的字符终点 (不含 join 空格)
        sel = di.loc[(di["pos"] < abs_end) & (word_end > abs_start)]
        if sel.empty:
            return di, None, None

        # mask 已匹配区域, 防止后续字符串重复命中 (长度不变, pos 索引仍有效)
        di.loc[sel.index, "content"] = [("|" * (int(l) - 1)) for l in sel["len"]]

        grouped = (
            sel.groupby("pageNumber", as_index=False)
            .agg({
                "x0": "min", "x1": "max",
                "y0": "min", "y1": "max",
                "unit": "first", "width": "first", "height": "first",
            })
            .to_dict(orient="records")
        )
        record = grouped[0] if grouped else None
        if not record:
            return di, None, None

        pageNumber = record.get("pageNumber")
        payload = {
            "x0": record.get("x0"), "x1": record.get("x1"),
            "y0": record.get("y0"), "y1": record.get("y1"),
            "unit": record.get("unit"),
            "pageWidth": record.get("width"),
            "pageHeight": record.get("height"),
        }
        return di, pageNumber, json.dumps(
            WorkerPool._to_bounding_box_storage_payload(payload), ensure_ascii=True
        )
