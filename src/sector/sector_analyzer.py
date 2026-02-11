# -*- coding: utf-8 -*-
"""
===================================
板块分析流水线
===================================

功能：
1. 整合板块数据获取 + 板块分析
2. 生成板块分析结果
3. 支持行业板块和概念板块分析
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from .sector_types import (
    SectorIndex,
    SectorType,
    SectorStockStats,
    SectorAnalysisResult,
    SectorSignalEvidence,
    MarketStatus,
    TrendStatus,
    SignalGrade,
)
from .sector_fetcher import SectorFetcher


logger = logging.getLogger(__name__)


@dataclass
class SectorAnalyzerConfig:
    """板块分析配置"""

    # 分析哪些类型的板块
    analyze_industry: bool = True
    analyze_concept: bool = True

    # 板块数量限制
    max_hot_sectors: int = 10

    # 大盘涨跌幅（用于计算相对强弱）
    market_index_change: float = 0.0

    # 信号阈值
    strong_bull_threshold: float = 3.0  # 相对大盘 > 3% 为领涨
    limit_up_ratio_threshold: float = 0.1  # 涨停家数/总家数 > 10% 为强势
    flow_direction_threshold: float = 0.5  # 主力流入/流出阈值（亿元）


class SectorAnalyzer:
    """板块分析器"""

    def __init__(self, config: Optional[SectorAnalyzerConfig] = None):
        """初始化板块分析器"""
        self.config = config or SectorAnalyzerConfig()
        self.fetcher = SectorFetcher()

    def analyze_sector(
        self,
        sector_code: str,
        sector_name: str,
        sector_type: SectorType,
        stock_codes: Optional[List[str]] = None,
    ) -> Optional[SectorAnalysisResult]:
        """分析单个板块

        Args:
            sector_code: 板块代码
            sector_name: 板块名称
            sector_type: 板块类型
            stock_codes: 要重点分析的股票代码列表（可选）

        Returns:
            SectorAnalysisResult: 板块分析结果
        """
        # 获取板块指数数据
        sector_index = self.fetcher.get_sector_index(
            sector_code=sector_code,
            sector_name=sector_name,
            sector_type=sector_type,
            market_index_change=self.config.market_index_change,
        )

        if sector_index is None:
            logger.warning(f"无法获取板块 {sector_name} ({sector_code}) 数据")
            return None

        # 获取领涨/领跌股票
        leading_stocks = self.fetcher.get_leading_stocks(sector_code, limit=5)

        # 分析成分股（如果有指定股票）
        abnormal_stocks = []
        if stock_codes:
            stats = self.fetcher.get_sector_stocks_data(sector_code, stock_codes)
            abnormal_stocks = [
                s for s in stats if s.is_abnormal or abs(s.change_pct) > 5
            ]

        # 计算市场状态
        market_status = self._calc_market_status(sector_index)

        # 计算趋势状态
        trend_status = self._calc_trend_status(sector_index)

        # 计算信号评分
        signal_score, signal_evidence = self._calc_signal_score(sector_index)

        # 确定信号等级
        signal_grade = self._calc_signal_grade(signal_score, market_status)

        # 计算资金流向
        flow_direction, flow_strength = self._calc_flow_direction(sector_index)

        # 风险与机会
        risk_factors, opportunities = self._calc_risk_opportunity(sector_index)

        # 操作建议
        action_advice, confidence, target_allocation = self._calc_action_advice(
            market_status, signal_grade, flow_direction
        )

        return SectorAnalysisResult(
            sector=sector_index,
            market_status=market_status,
            trend_status=trend_status,
            signal_score=signal_score,
            signal_grade=signal_grade,
            leading_stocks=leading_stocks,
            abnormal_stocks=abnormal_stocks,
            signal_evidence=signal_evidence,
            flow_direction=flow_direction,
            flow_strength=flow_strength,
            risk_factors=risk_factors,
            opportunities=opportunities,
            action_advice=action_advice,
            confidence=confidence,
            target_allocation=target_allocation,
        )

    def analyze_hot_sectors(
        self, sector_type: SectorType = SectorType.INDUSTRY, limit: int = 10
    ) -> List[SectorAnalysisResult]:
        """分析热门板块

        Args:
            sector_type: 板块类型
            limit: 分析数量限制

        Returns:
            List[SectorAnalysisResult]: 分析结果列表
        """
        # 获取热门板块排行
        if sector_type == SectorType.INDUSTRY:
            hot_sectors = self.fetcher.get_hot_sectors(limit=limit)
        else:
            # 概念板块暂时使用行业排行代替
            hot_sectors = self.fetcher.get_hot_sectors(limit=limit)

        results = []
        for sector in hot_sectors:
            result = self.analyze_sector(
                sector_code=sector["code"],
                sector_name=sector["name"],
                sector_type=sector_type,
            )
            if result:
                results.append(result)

        # 按信号评分排序
        results.sort(key=lambda x: x.signal_score, reverse=True)

        return results

    def analyze_portfolio_sectors(
        self, stock_codes: List[str], industry_codes: Optional[List[str]] = None
    ) -> Dict[str, SectorAnalysisResult]:
        """分析自选股所属板块

        Args:
            stock_codes: 自选股代码列表
            industry_codes: 要分析的板块代码列表（可选，默认分析所有涉及板块）

        Returns:
            Dict[str, SectorAnalysisResult]: {板块名称: 分析结果}
        """
        # 收集涉及的板块
        sector_map = {}
        for code in stock_codes:
            industries = self.fetcher.get_industry_tags(code)
            for industry in industries:
                if industry not in sector_map:
                    sector_map[industry] = []
                sector_map[industry].append(code)

        # 分析每个板块
        results = {}
        for sector_name, codes in sector_map.items():
            # 获取板块代码（简化处理，使用名称作为代码）
            sector_code = f"ind_{sector_name}"

            result = self.analyze_sector(
                sector_code=sector_code,
                sector_name=sector_name,
                sector_type=SectorType.INDUSTRY,
                stock_codes=codes,
            )
            if result:
                results[sector_name] = result

        return results

    def _calc_market_status(self, sector: SectorIndex) -> MarketStatus:
        """计算市场状态"""
        rel_strength = sector.relative_strength

        if rel_strength > self.config.strong_bull_threshold:
            return MarketStatus.LEADER_UP
        elif rel_strength > 0:
            return MarketStatus.FOLLOW_UP
        elif rel_strength < -self.config.strong_bull_threshold:
            return MarketStatus.LEADER_DOWN
        elif rel_strength < 0:
            return MarketStatus.FOLLOW_DOWN
        else:
            return MarketStatus.CONSOLIDATION

    def _calc_trend_status(self, sector: SectorIndex) -> TrendStatus:
        """计算趋势状态"""
        # 基于涨跌幅和强度评分判断
        change = sector.change_pct
        strength = sector.strength_score

        if strength >= 80 and change > 2:
            return TrendStatus.STRONG_BULL
        elif strength >= 60 and change > 0:
            return TrendStatus.BULL
        elif strength >= 40:
            return TrendStatus.CONSOLIDATION
        elif strength >= 20 and change < 0:
            return TrendStatus.WEAK_BEAR
        else:
            return TrendStatus.BEAR

    def _calc_signal_score(self, sector: SectorIndex) -> tuple:
        """计算信号评分和证据"""
        score = 0
        evidence = []

        # 1. 相对强弱 (30分)
        rel_strength = sector.relative_strength
        if rel_strength > 5:
            rs_score = 30
        elif rel_strength > 3:
            rs_score = 25
        elif rel_strength > 0:
            rs_score = 20
        elif rel_strength > -3:
            rs_score = 10
        else:
            rs_score = 0
        score += rs_score
        evidence.append(
            SectorSignalEvidence(
                signal_type="relative_strength",
                description=f"相对大盘强弱",
                value=rel_strength,
                threshold=3.0,
                direction="正向" if rel_strength > 0 else "负向",
                score_contribution=rs_score,
                weight=30,
            )
        )

        # 2. 涨停比例 (20分)
        if sector.stock_count > 0:
            limit_up_ratio = sector.limit_up_count / sector.stock_count
            if limit_up_ratio >= 0.15:
                lu_score = 20
            elif limit_up_ratio >= 0.1:
                lu_score = 15
            elif limit_up_ratio >= 0.05:
                lu_score = 10
            else:
                lu_score = 5
            score += lu_score
            evidence.append(
                SectorSignalEvidence(
                    signal_type="limit_up_ratio",
                    description="涨停家数占比",
                    value=limit_up_ratio,
                    threshold=0.1,
                    direction="正向" if limit_up_ratio > 0.05 else "中性",
                    score_contribution=lu_score,
                    weight=20,
                )
            )

        # 3. 涨跌家数比 (20分)
        if sector.up_count + sector.down_count > 0:
            up_ratio = sector.up_count / (sector.up_count + sector.down_count)
            if up_ratio >= 0.7:
                up_score = 20
            elif up_ratio >= 0.6:
                up_score = 15
            elif up_ratio >= 0.4:
                up_score = 10
            else:
                up_score = 5
            score += up_score
            evidence.append(
                SectorSignalEvidence(
                    signal_type="up_down_ratio",
                    description="上涨家数占比",
                    value=up_ratio,
                    threshold=0.6,
                    direction="正向" if up_ratio > 0.5 else "负向",
                    score_contribution=up_score,
                    weight=20,
                )
            )

        # 4. 板块强度 (20分)
        strength = sector.strength_score
        if strength >= 80:
            st_score = 20
        elif strength >= 60:
            st_score = 15
        elif strength >= 40:
            st_score = 10
        else:
            st_score = 5
        score += st_score
        evidence.append(
            SectorSignalEvidence(
                signal_type="strength_score",
                description="板块强度评分",
                value=strength,
                threshold=60,
                direction="正向" if strength > 50 else "负向",
                score_contribution=st_score,
                weight=20,
            )
        )

        # 5. 量能 (10分)
        if sector.turnover_rate >= 3:
            vol_score = 10
        elif sector.turnover_rate >= 2:
            vol_score = 7
        elif sector.turnover_rate >= 1:
            vol_score = 5
        else:
            vol_score = 3
        score += vol_score
        evidence.append(
            SectorSignalEvidence(
                signal_type="turnover_rate",
                description="板块换手率",
                value=sector.turnover_rate,
                threshold=2.0,
                direction="正向" if sector.turnover_rate > 1 else "中性",
                score_contribution=vol_score,
                weight=10,
            )
        )

        return score, evidence

    def _calc_signal_grade(
        self, score: int, market_status: MarketStatus
    ) -> SignalGrade:
        """计算信号等级"""
        if score >= 80 and market_status in [MarketStatus.LEADER_UP]:
            return SignalGrade.STRONG_BULLISH
        elif score >= 60 and market_status in [
            MarketStatus.LEADER_UP,
            MarketStatus.FOLLOW_UP,
        ]:
            return SignalGrade.BULLISH
        elif score >= 40:
            return SignalGrade.NEUTRAL
        elif score >= 20:
            return SignalGrade.BEARISH
        else:
            return SignalGrade.STRONG_BEARISH

    def _calc_flow_direction(self, sector: SectorIndex) -> tuple:
        """计算资金流向"""
        flow = sector.main_flow

        if flow > 5:
            return "流入", "大幅流入"
        elif flow > 1:
            return "流入", "温和流入"
        elif flow >= -1:
            return "持平", "持平"
        elif flow >= -5:
            return "流出", "温和流出"
        else:
            return "流出", "大幅流出"

    def _calc_risk_opportunity(self, sector: SectorIndex) -> tuple:
        """计算风险与机会"""
        risks = []
        opportunities = []

        # 风险
        if sector.change_pct > 5:
            risks.append(f"短期涨幅过大（{sector.change_pct:.1f}%），谨防回调")
        if sector.limit_down_count > sector.limit_up_count / 2:
            risks.append("跌停家数较多，注意风险")
        if sector.relative_strength < -3:
            risks.append("相对大盘走势较弱")

        # 机会
        if sector.change_pct < -3 and sector.relative_strength > -1:
            opportunities.append("相对大盘抗跌，可能率先反弹")
        if sector.limit_up_count > sector.stock_count * 0.1:
            opportunities.append("涨停家数较多，市场热度高")
        if sector.up_ratio > 0.6:
            opportunities.append("上涨家数占优，板块情绪偏多")

        return risks, opportunities

    def _calc_action_advice(
        self,
        market_status: MarketStatus,
        signal_grade: SignalGrade,
        flow_direction: str,
    ) -> tuple:
        """计算操作建议"""
        if signal_grade == SignalGrade.STRONG_BULLISH:
            if flow_direction == "流入":
                return "增持", "高", "可加仓至目标仓位"
            else:
                return "持有", "中", "维持当前仓位"
        elif signal_grade == SignalGrade.BULLISH:
            return "持有", "中", "维持当前仓位"
        elif signal_grade == SignalGrade.NEUTRAL:
            return "观望", "中", "等待更明确信号"
        elif signal_grade == SignalGrade.BEARISH:
            return "减仓", "中", "可适当减仓避险"
        else:
            return "减持", "高", "建议减仓或清仓"
