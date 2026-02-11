# -*- coding: utf-8 -*-
"""
===================================
行业/概念/风格标签体系
===================================

功能：
1. 为股票添加行业分类标签
2. 为股票添加概念板块标签
3. 为股票判断投资风格（成长/价值/周期/红利）
4. 为股票判断市值分类（大/中/小盘）

依赖：
- akshare
"""

import logging
from typing import List, Optional, Dict, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

try:
    import akshare as ak
except ImportError:
    ak = None


logger = logging.getLogger(__name__)


class TagType(Enum):
    """标签类型"""

    INDUSTRY = "行业"  # 申万/同花顺行业
    CONCEPT = "概念"  # 概念板块
    STYLE = "风格"  # 成长/价值/周期/红利
    MARKET_CAP = "市值"  # 大/中/小盘


class MarketCapBucket(Enum):
    """市值分类"""

    LARGE = "大盘"  # >1000亿
    MID = "中盘"  # 200-1000亿
    SMALL = "小盘"  # <200亿


class InvestmentStyle(Enum):
    """投资风格"""

    GROWTH = "成长"  # 高增速、高估值
    VALUE = "价值"  # 低估值、高股息
    CYCLICAL = "周期"  # 强周期性行业
    DIVIDEND = "红利"  # 稳定分红
    TECH = "科技"  # 高研发投入
    CONSUMER = "消费"  # 消费行业
    FINANCIAL = "金融"  # 银行/券商/保险
    ENERGY = "能源"  # 石油/煤炭/新能源


@dataclass
class StockTags:
    """股票标签数据"""

    code: str  # 股票代码
    name: str  # 股票名称

    # 行业标签
    industries: List[str] = field(default_factory=list)  # ["半导体", "电子元件"]
    industry_codes: List[str] = field(default_factory=list)  # ["801080", "801070"]

    # 概念标签
    concepts: List[str] = field(default_factory=list)  # ["新能源", "AI概念"]
    concept_codes: List[str] = field(default_factory=list)  # ["881001", "881002"]

    # 风格标签
    styles: List[InvestmentStyle] = field(
        default_factory=list
    )  # [InvestmentStyle.GROWTH]

    # 市值分类
    market_cap_bucket: MarketCapBucket = MarketCapBucket.SMALL
    market_cap: float = 0.0  # 市值（亿元）

    # 其他标签
    is_st: bool = False  # 是否 ST
    is_new: bool = False  # 是否次新股（上市 < 1年）
    is_hs300: bool = False  # 是否沪深300成分
    is_zz500: bool = False  # 是否中证500成分

    # 时间戳
    tagged_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, any]:
        return {
            "code": self.code,
            "name": self.name,
            "industries": self.industries,
            "industry_codes": self.industry_codes,
            "concepts": self.concepts,
            "concept_codes": self.concept_codes,
            "styles": [s.value for s in self.styles],
            "market_cap_bucket": self.market_cap_bucket.value,
            "market_cap": self.market_cap,
            "is_st": self.is_st,
            "is_new": self.is_new,
            "is_hs300": self.is_hs300,
            "is_zz500": self.is_zz500,
            "tagged_at": self.tagged_at,
        }

    def get_all_tags(self) -> Set[str]:
        """获取所有标签"""
        tags = set(self.industries)
        tags.update(self.concepts)
        tags.update([s.value for s in self.styles])
        tags.add(self.market_cap_bucket.value)
        return tags


class IndustryTagger:
    """行业标签生成器"""

    # 风格映射规则
    STYLE_MAPPING = {
        # 成长风格行业
        "科技": [InvestmentStyle.TECH, InvestmentStyle.GROWTH],
        "半导体": [InvestmentStyle.TECH, InvestmentStyle.GROWTH],
        "软件开发": [InvestmentStyle.TECH, InvestmentStyle.GROWTH],
        "互联网": [InvestmentStyle.TECH, InvestmentStyle.GROWTH],
        "通信设备": [InvestmentStyle.TECH],
        # 消费风格行业
        "食品饮料": [InvestmentStyle.CONSUMER, InvestmentStyle.DIVIDEND],
        "家用电器": [InvestmentStyle.CONSUMER, InvestmentStyle.VALUE],
        "纺织服装": [InvestmentStyle.CONSUMER],
        "休闲服务": [InvestmentStyle.CONSUMER],
        "商贸零售": [InvestmentStyle.CONSUMER],
        # 金融风格行业
        "银行": [
            InvestmentStyle.FINANCIAL,
            InvestmentStyle.DIVIDEND,
            InvestmentStyle.VALUE,
        ],
        "证券": [InvestmentStyle.FINANCIAL],
        "保险": [InvestmentStyle.FINANCIAL],
        "多元金融": [InvestmentStyle.FINANCIAL],
        # 周期风格行业
        "煤炭": [InvestmentStyle.CYCLICAL, InvestmentStyle.DIVIDEND],
        "有色金属": [InvestmentStyle.CYCLICAL],
        "钢铁": [InvestmentStyle.CYCLICAL],
        "化工": [InvestmentStyle.CYCLICAL],
        "石油石化": [InvestmentStyle.CYCLICAL, InvestmentStyle.DIVIDEND],
        "交通运输": [InvestmentStyle.CYCLICAL],
        "房地产": [InvestmentStyle.CYCLICAL],
        "建筑材料": [InvestmentStyle.CYCLICAL],
        # 医药风格
        "医疗器械": [InvestmentStyle.GROWTH],
        "化学制药": [InvestmentStyle.GROWTH],
        "中药": [InvestmentStyle.VALUE, InvestmentStyle.DIVIDEND],
        "生物制品": [InvestmentStyle.GROWTH],
        # 新能源风格
        "光伏设备": [InvestmentStyle.GROWTH],
        "电池": [InvestmentStyle.GROWTH],
        "风电设备": [InvestmentStyle.GROWTH],
        "储能": [InvestmentStyle.GROWTH],
        # 公用事业风格
        "电力": [InvestmentStyle.DIVIDEND, InvestmentStyle.VALUE],
        "燃气": [InvestmentStyle.DIVIDEND],
        "水务": [InvestmentStyle.DIVIDEND],
        "环保": [InvestmentStyle.VALUE],
    }

    # 高股息行业
    HIGH_DIVIDEND_INDUSTRIES = {
        "煤炭",
        "石油石化",
        "银行",
        "电力",
        "通信",
        "交通设施",
        "家电",
        "食品饮料",
        "医药商业",
        "化学制药",
        "水务",
        "燃气",
    }

    def __init__(self):
        self._industry_cache: Dict[str, List[Dict]] = {}
        self._concept_cache: Dict[str, List[Dict]] = {}

    def _check_akshare(self) -> bool:
        if ak is None:
            logger.warning("AkShare 未安装，无法获取行业/概念标签")
            return False
        return True

    def _get_industries_from_akshare(self, code: str) -> List[Dict]:
        """从 AkShare 获取股票行业分类"""
        if not self._check_akshare():
            return []

        cache_key = f"industry_{code}"
        if cache_key in self._industry_cache:
            return self._industry_cache[cache_key]

        try:
            # 使用同花顺行业分类
            df = ak.stock_board_cons_ths(symbol="行业分类")
            if df is not None and not df.empty:
                result = []
                for _, row in df.iterrows():
                    stock_code = str(row.get("代码", ""))
                    if "." in stock_code:
                        stock_code = stock_code.split(".")[0]
                    if stock_code == code:
                        industry_name = row.get("名称", "")
                        industry_code = str(row.get("代码", ""))
                        if industry_name:
                            result.append(
                                {
                                    "name": industry_name,
                                    "code": industry_code,
                                }
                            )

                self._industry_cache[cache_key] = result
                return result
        except Exception as e:
            logger.debug(f"获取股票 {code} 行业分类失败: {e}")

        self._industry_cache[cache_key] = []
        return []

    def _get_concepts_from_akshare(self, code: str) -> List[Dict]:
        """从 AkShare 获取股票概念板块"""
        if not self._check_akshare():
            return []

        cache_key = f"concept_{code}"
        if cache_key in self._concept_cache:
            return self._concept_cache[cache_key]

        try:
            df = ak.stock_board_cons_ths(symbol="概念分类")
            if df is not None and not df.empty:
                result = []
                for _, row in df.iterrows():
                    stock_code = str(row.get("代码", ""))
                    if "." in stock_code:
                        stock_code = stock_code.split(".")[0]
                    if stock_code == code:
                        concept_name = row.get("名称", "")
                        concept_code = str(row.get("代码", ""))
                        if concept_name:
                            result.append(
                                {
                                    "name": concept_name,
                                    "code": concept_code,
                                }
                            )

                self._concept_cache[cache_key] = result
                return result
        except Exception as e:
            logger.debug(f"获取股票 {code} 概念分类失败: {e}")

        self._concept_cache[cache_key] = []
        return []

    def _infer_styles(
        self, industries: List[str], market_cap: float
    ) -> List[InvestmentStyle]:
        """推断投资风格"""
        styles = []

        for industry in industries:
            for key, mapping in self.STYLE_MAPPING.items():
                if key in industry:
                    styles.extend(mapping)

        # 如果没有匹配的行业风格，基于市值和行业关键词推断
        if not styles:
            if market_cap > 500:  # 大市值
                if any(
                    kw in str(industries) for kw in ["银行", "保险", "电力", "通信"]
                ):
                    styles.append(InvestmentStyle.VALUE)
                else:
                    styles.append(InvestmentStyle.GROWTH)
            else:  # 中小市值
                styles.append(InvestmentStyle.GROWTH)

        # 高股息风格判断
        if any(ind in industries for ind in self.HIGH_DIVIDEND_INDUSTRIES):
            if InvestmentStyle.DIVIDEND not in styles:
                styles.append(InvestmentStyle.DIVIDEND)

        # 去重并保持顺序
        seen = set()
        unique_styles = []
        for s in styles:
            if s not in seen:
                seen.add(s)
                unique_styles.append(s)

        return unique_styles

    def get_industry_tags(self, code: str, name: str = "") -> List[str]:
        """获取股票行业标签"""
        industries = self._get_industries_from_akshare(code)
        return [ind["name"] for ind in industries]

    def get_concept_tags(self, code: str) -> List[str]:
        """获取股票概念标签"""
        concepts = self._get_concepts_from_akshare(code)
        return [c["name"] for c in concepts]

    def get_stock_tags(
        self, code: str, name: str = "", market_cap: float = 0.0
    ) -> StockTags:
        """获取股票完整标签"""
        industries = self._get_industries_from_akshare(code)
        concepts = self._get_concepts_from_akshare(code)

        industry_names = [ind["name"] for ind in industries]
        industry_codes = [ind["code"] for ind in industries]
        concept_names = [c["name"] for c in concepts]
        concept_codes = [c["code"] for c in concepts]

        # 判断市值分类
        if market_cap > 1000:
            mcap_bucket = MarketCapBucket.LARGE
        elif market_cap > 200:
            mcap_bucket = MarketCapBucket.MID
        else:
            mcap_bucket = MarketCapBucket.SMALL

        # 推断风格
        styles = self._infer_styles(industry_names, market_cap)

        return StockTags(
            code=code,
            name=name,
            industries=industry_names,
            industry_codes=industry_codes,
            concepts=concept_names,
            concept_codes=concept_codes,
            styles=styles,
            market_cap_bucket=mcap_bucket,
            market_cap=market_cap,
        )

    def get_portfolio_sector_mapping(
        self, stock_codes: List[str]
    ) -> Dict[str, List[str]]:
        """获取自选股的板块映射

        Returns:
            Dict: {板块名称: [股票代码列表]}
        """
        sector_map = {}

        for code in stock_codes:
            industries = self.get_industry_tags(code)
            for industry in industries:
                if industry not in sector_map:
                    sector_map[industry] = []
                if code not in sector_map[industry]:
                    sector_map[industry].append(code)

        return sector_map


# 全局标签器实例
_tagger: Optional[IndustryTagger] = None


def get_tagger() -> IndustryTagger:
    """获取全局标签器实例"""
    global _tagger
    if _tagger is None:
        _tagger = IndustryTagger()
    return _tagger


def get_stock_tags(code: str, name: str = "", market_cap: float = 0.0) -> StockTags:
    """便捷函数：获取股票标签"""
    return get_tagger().get_stock_tags(code, name, market_cap)
