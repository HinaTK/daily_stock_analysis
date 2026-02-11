# -*- coding: utf-8 -*-
"""
===================================
标签体系模块
===================================

子模块：
- industry_tagger: 行业/概念/风格标签
"""

from .industry_tagger import (
    IndustryTagger,
    StockTags,
    TagType,
    MarketCapBucket,
    InvestmentStyle,
    get_stock_tags,
)

__all__ = [
    "IndustryTagger",
    "StockTags",
    "TagType",
    "MarketCapBucket",
    "InvestmentStyle",
    "get_stock_tags",
]
