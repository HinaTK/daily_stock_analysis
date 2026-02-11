# -*- coding: utf-8 -*-
"""
===================================
板块分析数据类型定义
===================================

包含：
- 板块指数数据 (SectorIndex)
- 板块分析结果 (SectorAnalysisResult)
- 成分股统计 (SectorStockStats)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class SectorType(Enum):
    """板块类型"""
    INDUSTRY = "industry"      # 行业板块
    CONCEPT = "concept"       # 概念板块
    STYLE = "style"           # 风格板块
    THEME = "theme"           # 主题板块


class MarketStatus(Enum):
    """大盘/板块市场状态"""
    LEADER_UP = "领涨"        # 涨幅超过大盘
    FOLLOW_UP = "跟涨"        # 跟随大盘上涨
    CONSOLIDATION = "震荡"    # 震荡整理
    FOLLOW_DOWN = "跟跌"      # 跟随大盘下跌
    LEADER_DOWN = "领跌"      # 跌幅超过大盘


class TrendStatus(Enum):
    """趋势状态"""
    STRONG_BULL = "强势多头"
    BULL = "多头排列"
    WEAK_BULL = "弱势多头"
    CONSOLIDATION = "盘整"
    WEAK_BEAR = "弱势空头"
    BEAR = "空头排列"
    STRONG_BEAR = "强势空头"


class SignalGrade(Enum):
    """信号等级"""
    STRONG_BULLISH = "强看多"
    BULLISH = "看多"
    NEUTRAL = "中性"
    BEARISH = "看空"
    STRONG_BEARISH = "强看空"


@dataclass
class SectorIndex:
    """板块指数数据"""
    sector_code: str           # 板块代码
    sector_name: str           # 板块名称
    sector_type: SectorType    # 板块类型
    
    # 行情数据
    current: float = 0.0       # 当前点位/均价
    change_pct: float = 0.0    # 涨跌幅
    turnover_rate: float = 0.0  # 板块换手率
    
    # 统计特征
    up_count: int = 0          # 上涨家数
    down_count: int = 0        # 下跌家数
    limit_up_count: int = 0     # 涨停家数
    limit_down_count: int = 0   # 跌停家数
    avg_change: float = 0.0     # 板块平均涨幅
    
    # 资金流向
    main_flow: float = 0.0     # 主力净流入 (亿元)
    north_flow: float = 0.0     # 北向净流入 (亿元)
    
    # 强度指标
    strength_score: float = 0.0  # 板块强度 0-100
    relative_strength: float = 0.0  # 相对大盘强弱
    
    # 关联数据
    stock_count: int = 0       # 成分股数量
    market_cap: float = 0.0     # 板块总市值 (亿元)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sector_code': self.sector_code,
            'sector_name': self.sector_name,
            'sector_type': self.sector_type.value,
            'current': self.current,
            'change_pct': self.change_pct,
            'turnover_rate': self.turnover_rate,
            'up_count': self.up_count,
            'down_count': self.down_count,
            'limit_up_count': self.limit_up_count,
            'limit_down_count': self.limit_down_count,
            'avg_change': self.avg_change,
            'main_flow': self.main_flow,
            'north_flow': self.north_flow,
            'strength_score': self.strength_score,
            'relative_strength': self.relative_strength,
            'stock_count': self.stock_count,
            'market_cap': self.market_cap,
        }


@dataclass
class SectorStockStats:
    """成分股统计"""
    code: str                    # 股票代码
    name: str                    # 股票名称
    change_pct: float = 0.0     # 涨跌幅
    is_limit_up: bool = False    # 是否涨停
    is_limit_down: bool = False  # 是否跌停
    is_leading: bool = False     # 是否领涨
    is_lagging: bool = False     # 是否领跌
    is_abnormal: bool = False    # 是否异常放量
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'change_pct': self.change_pct,
            'is_limit_up': self.is_limit_up,
            'is_limit_down': self.is_limit_down,
            'is_leading': self.is_leading,
            'is_lagging': self.is_lagging,
            'is_abnormal': self.is_abnormal,
        }


@dataclass
class SectorSignalEvidence:
    """板块信号证据"""
    signal_type: str             # 信号类型
    description: str            # 描述
    value: float               # 实际值
    threshold: float           # 阈值
    direction: str              # "正向" / "负向" / "中性"
    score_contribution: float   # 得分贡献
    weight: float              # 权重
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'signal_type': self.signal_type,
            'description': self.description,
            'value': self.value,
            'threshold': self.threshold,
            'direction': self.direction,
            'score_contribution': self.score_contribution,
            'weight': self.weight,
        }


@dataclass
class SectorAnalysisResult:
    """板块分析结果"""
    sector: SectorIndex
    
    # 市场状态
    market_status: MarketStatus = MarketStatus.CONSOLIDATION
    trend_status: TrendStatus = TrendStatus.CONSOLIDATION
    
    # 信号评分
    signal_score: int = 0
    signal_grade: SignalGrade = SignalGrade.NEUTRAL
    
    # 成分股分析
    leading_stocks: List[SectorStockStats] = field(default_factory=list)
    lagging_stocks: List[SectorStockStats] = field(default_factory=list)
    abnormal_stocks: List[SectorStockStats] = field(default_factory=list)
    
    # 资金流向
    flow_direction: str = "持平"
    flow_strength: str = "温和"
    consecutive_days: int = 0  # 连续流入/流出天数
    
    # 信号证据
    signal_evidence: List[SectorSignalEvidence] = field(default_factory=list)
    
    # 风险与机会
    risk_factors: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    
    # 操作建议
    action_advice: str = "观望"
    confidence: str = "中"
    target_allocation: str = "维持当前"
    
    # 时间戳
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sector': self.sector.to_dict(),
            'market_status': self.market_status.value,
            'trend_status': self.trend_status.value,
            'signal_score': self.signal_score,
            'signal_grade': self.signal_grade.value,
            'leading_stocks': [s.to_dict() for s in self.leading_stocks],
            'lagging_stocks': [s.to_dict() for s in self.lagging_stocks],
            'abnormal_stocks': [s.to_dict() for s in self.abnormal_stocks],
            'flow_direction': self.flow_direction,
            'flow_strength': self.flow_strength,
            'consecutive_days': self.consecutive_days,
            'signal_evidence': [e.to_dict() for e in self.signal_evidence],
            'risk_factors': self.risk_factors,
            'opportunities': self.opportunities,
            'action_advice': self.action_advice,
            'confidence': self.confidence,
            'target_allocation': self.target_allocation,
            'updated_at': self.updated_at,
        }


@dataclass
class PortfolioSectorView:
    """自选股+板块联动视图"""
    stock_code: str              # 股票代码
    stock_name: str              # 股票名称
    
    # 个股数据
    stock_change_pct: float = 0.0  # 个股涨跌幅
    stock_signal: str = "观望"     # 个股信号
    
    # 板块数据
    sector_code: str = ""         # 所属板块代码
    sector_name: str = ""         # 所属板块名称
    sector_type: SectorType = SectorType.INDUSTRY
    sector_change_pct: float = 0.0  # 板块涨跌幅
    sector_signal: str = "中性"    # 板块信号
    
    # 相对表现
    relative_performance: float = 0.0  # 个股相对板块涨跌
    
    # 板块对个股的影响
    sector_impact: str = "中性"      # "正向" / "负向" / "中性"
    impact_reason: str = ""          # 影响原因
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'stock_change_pct': self.stock_change_pct,
            'stock_signal': self.stock_signal,
            'sector_code': self.sector_code,
            'sector_name': self.sector_name,
            'sector_type': self.sector_type.value,
            'sector_change_pct': self.sector_change_pct,
            'sector_signal': self.sector_signal,
            'relative_performance': self.relative_performance,
            'sector_impact': self.sector_impact,
            'impact_reason': self.impact_reason,
        }
