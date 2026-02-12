# -*- coding: utf-8 -*-
"""
==================================
趋势交易分析器 - 基于用户交易理念
==================================

交易理念核心原则：
1. 严进策略 - 不追高，追求每笔交易成功率
2. 趋势交易 - MA5>MA10>MA20 多头排列，顺势而为
3. 效率优先 - 关注筹码结构好的股票
4. 买点偏好 - 在 MA5/MA10 附近回踩买入

技术标准：
- 多头排列：MA5 > MA10 > MA20
- 乖离率：(Close - MA5) / MA5 < 5%（不追高）
- 量能形态：缩量回调优先

支持 YAML 配置（src/analyzer_config/analyzer_rules.yaml）
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

import pandas as pd
import numpy as np

# 尝试导入 YAML 配置（支持可选）
YAML_CONFIG_AVAILABLE = False
AnalyzerRules = None

try:
    from analyzer_config.config_loader import (
        get_analyzer_rules,
        AnalyzerRules,
    )

    YAML_CONFIG_AVAILABLE = True
except ImportError:
    pass

# 尝试导入信号证据模块
generate_signal_evidence = None
try:
    from analysis_ext import generate_signal_evidence

    EVIDENCE_AVAILABLE = True
except ImportError:
    EVIDENCE_AVAILABLE = False

logger = logging.getLogger(__name__)


class TrendStatus(Enum):
    """趋势状态枚举"""

    STRONG_BULL = "强势多头"  # MA5 > MA10 > MA20，且间距扩大
    BULL = "多头排列"  # MA5 > MA10 > MA20
    WEAK_BULL = "弱势多头"  # MA5 > MA10，但 MA10 < MA20
    CONSOLIDATION = "盘整"  # 均线缠绕
    WEAK_BEAR = "弱势空头"  # MA5 < MA10，但 MA10 > MA20
    BEAR = "空头排列"  # MA5 < MA10 < MA20
    STRONG_BEAR = "强势空头"  # MA5 < MA10 < MA20，且间距扩大


class VolumeStatus(Enum):
    """量能状态枚举"""

    HEAVY_VOLUME_UP = "放量上涨"  # 量价齐升
    HEAVY_VOLUME_DOWN = "放量下跌"  # 放量杀跌
    SHRINK_VOLUME_UP = "缩量上涨"  # 无量上涨
    SHRINK_VOLUME_DOWN = "缩量回调"  # 缩量回调（好）
    NORMAL = "量能正常"


class BuySignal(Enum):
    """买入信号枚举"""

    STRONG_BUY = "强烈买入"  # 多条件满足
    BUY = "买入"  # 基本条件满足
    HOLD = "持有"  # 已持有可继续
    WAIT = "观望"  # 等待更好时机
    SELL = "卖出"  # 趋势转弱
    STRONG_SELL = "强烈卖出"  # 趋势破坏


class MACDStatus(Enum):
    """MACD状态枚举"""

    GOLDEN_CROSS_ZERO = "零轴上金叉"  # DIF上穿DEA，且在零轴上方
    GOLDEN_CROSS = "金叉"  # DIF上穿DEA
    BULLISH = "多头"  # DIF>DEA>0
    CROSSING_UP = "上穿零轴"  # DIF上穿零轴
    CROSSING_DOWN = "下穿零轴"  # DIF下穿零轴
    BEARISH = "空头"  # DIF<DEA<0
    DEATH_CROSS = "死叉"  # DIF下穿DEA


class RSIStatus(Enum):
    """RSI状态枚举"""

    OVERBOUGHT = "超买"  # RSI > 70
    STRONG_BUY = "强势买入"  # 50 < RSI < 70
    NEUTRAL = "中性"  # 40 <= RSI <= 60
    WEAK = "弱势"  # 30 < RSI < 40
    OVERSOLD = "超卖"  # RSI < 30


@dataclass
class TrendAnalysisResult:
    """趋势分析结果"""

    code: str

    # 趋势判断
    trend_status: TrendStatus = TrendStatus.CONSOLIDATION
    ma_alignment: str = ""  # 均线排列描述
    trend_strength: float = 0.0  # 趋势强度 0-100

    # 均线数据
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    current_price: float = 0.0

    # 乖离率（与 MA5 的偏离度）
    bias_ma5: float = 0.0  # (Close - MA5) / MA5 * 100
    bias_ma10: float = 0.0
    bias_ma20: float = 0.0

    # 量能分析
    volume_status: VolumeStatus = VolumeStatus.NORMAL
    volume_ratio_5d: float = 0.0  # 当日成交量/5日均量
    volume_trend: str = ""  # 量能趋势描述

    # 支撑压力
    support_ma5: bool = False  # MA5 是否构成支撑
    support_ma10: bool = False  # MA10 是否构成支撑
    resistance_levels: List[float] = field(default_factory=list)
    support_levels: List[float] = field(default_factory=list)

    # MACD 指标
    macd_dif: float = 0.0  # DIF 快线
    macd_dea: float = 0.0  # DEA 慢线
    macd_bar: float = 0.0  # MACD 柱状图
    macd_status: MACDStatus = MACDStatus.BULLISH
    macd_signal: str = ""  # MACD 信号描述

    # RSI 指标
    rsi_6: float = 0.0  # RSI(6) 短期
    rsi_12: float = 0.0  # RSI(12) 中期
    rsi_24: float = 0.0  # RSI(24) 长期
    rsi_status: RSIStatus = RSIStatus.NEUTRAL
    rsi_signal: str = ""  # RSI 信号描述

    # ATR 风险指标
    atr_14: float = 0.0
    atr_stop_loss: float = 0.0

    # 布林带
    boll_mid: float = 0.0
    boll_upper: float = 0.0
    boll_lower: float = 0.0
    boll_position: str = "中轨附近"

    # KDJ
    k_value: float = 0.0
    d_value: float = 0.0
    j_value: float = 0.0
    kdj_status: str = "中性"

    # OBV
    obv_value: float = 0.0
    obv_trend: str = "中性"

    # 买入信号
    buy_signal: BuySignal = BuySignal.WAIT
    signal_score: int = 0  # 综合评分 0-100
    signal_reasons: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)

    # 信号证据（支持 YAML 配置）
    signal_evidence: Optional[Dict[str, Any]] = None

    # 行业/风格标签
    sector_tags: Optional[Dict[str, Any]] = None

    # 多周期共振
    timeframe_alignment: bool = False
    timeframe_notes: List[str] = field(default_factory=list)

    # 资金流向
    main_fund_net_inflow: float = 0.0
    main_fund_inflow_ratio: float = 0.0
    northbound_net_inflow: float = 0.0

    # 多信号共振统计
    resonance_count: int = 0
    resonance_passed: bool = False

    # 信号衰减
    signal_age_days: int = 0
    signal_valid: bool = True

    # 交易操作清单
    entry_price: float = 0.0
    stop_loss_price: float = 0.0
    target_price: float = 0.0
    recommended_position_pct: float = 0.0
    risk_reward_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "trend_status": self.trend_status.value,
            "ma_alignment": self.ma_alignment,
            "trend_strength": self.trend_strength,
            "ma5": self.ma5,
            "ma10": self.ma10,
            "ma20": self.ma20,
            "ma60": self.ma60,
            "current_price": self.current_price,
            "bias_ma5": self.bias_ma5,
            "bias_ma10": self.bias_ma10,
            "bias_ma20": self.bias_ma20,
            "volume_status": self.volume_status.value,
            "volume_ratio_5d": self.volume_ratio_5d,
            "volume_trend": self.volume_trend,
            "support_ma5": self.support_ma5,
            "support_ma10": self.support_ma10,
            "buy_signal": self.buy_signal.value,
            "signal_score": self.signal_score,
            "signal_reasons": self.signal_reasons,
            "risk_factors": self.risk_factors,
            "macd_dif": self.macd_dif,
            "macd_dea": self.macd_dea,
            "macd_bar": self.macd_bar,
            "macd_status": self.macd_status.value,
            "macd_signal": self.macd_signal,
            "rsi_6": self.rsi_6,
            "rsi_12": self.rsi_12,
            "rsi_24": self.rsi_24,
            "rsi_status": self.rsi_status.value,
            "rsi_signal": self.rsi_signal,
            "atr_14": self.atr_14,
            "atr_stop_loss": self.atr_stop_loss,
            "boll_mid": self.boll_mid,
            "boll_upper": self.boll_upper,
            "boll_lower": self.boll_lower,
            "boll_position": self.boll_position,
            "k_value": self.k_value,
            "d_value": self.d_value,
            "j_value": self.j_value,
            "kdj_status": self.kdj_status,
            "obv_value": self.obv_value,
            "obv_trend": self.obv_trend,
            "signal_evidence": self.signal_evidence,
            "sector_tags": self.sector_tags,
            "timeframe_alignment": self.timeframe_alignment,
            "timeframe_notes": self.timeframe_notes,
            "main_fund_net_inflow": self.main_fund_net_inflow,
            "main_fund_inflow_ratio": self.main_fund_inflow_ratio,
            "northbound_net_inflow": self.northbound_net_inflow,
            "resonance_count": self.resonance_count,
            "resonance_passed": self.resonance_passed,
            "signal_age_days": self.signal_age_days,
            "signal_valid": self.signal_valid,
            "entry_price": self.entry_price,
            "stop_loss_price": self.stop_loss_price,
            "target_price": self.target_price,
            "recommended_position_pct": self.recommended_position_pct,
            "risk_reward_ratio": self.risk_reward_ratio,
        }


class StockTrendAnalyzer:
    """
    股票趋势分析器

    基于用户交易理念实现：
    1. 趋势判断 - MA5>MA10>MA20 多头排列
    2. 乖离率检测 - 不追高，偏离 MA5 超过 5% 不买
    3. 量能分析 - 偏好缩量回调
    4. 买点识别 - 回踩 MA5/MA10 支撑
    5. MACD 指标 - 趋势确认和金叉死叉信号
    6. RSI 指标 - 超买超卖判断

    支持 YAML 配置（src/analyzer_config/analyzer_rules.yaml）：
    - 默认使用类属性配置
    - 如果 YAML 配置可用，则优先使用 YAML 配置
    - 支持环境变量覆盖
    """

    # 交易参数配置（默认值）
    BIAS_THRESHOLD = 5.0  # 乖离率阈值（%），超过此值不买入
    VOLUME_SHRINK_RATIO = 0.7  # 缩量判断阈值（当日量/5日均量）
    VOLUME_HEAVY_RATIO = 1.5  # 放量判断阈值
    MA_SUPPORT_TOLERANCE = 0.02  # MA 支撑判断容忍度（2%）

    # MACD 参数（标准12/26/9）
    MACD_FAST = 12  # 快线周期
    MACD_SLOW = 26  # 慢线周期
    MACD_SIGNAL = 9  # 信号线周期

    # RSI 参数
    RSI_SHORT = 6  # 短期RSI周期
    RSI_MID = 12  # 中期RSI周期
    RSI_LONG = 24  # 长期RSI周期
    RSI_OVERBOUGHT = 70  # 超买阈值
    RSI_OVERSOLD = 30  # 超卖阈值

    # ATR 风控参数
    ATR_PERIOD = 14
    ATR_STOP_MULTIPLIER = 2.0
    TARGET_PROFIT_MULTIPLIER = 3.0

    # 布林带参数
    BOLL_PERIOD = 20
    BOLL_STD = 2.0

    # 信号衰减参数
    SIGNAL_EXPIRY_DAYS = 5

    def __init__(self, style: str = "", use_yaml: Optional[bool] = None):
        """初始化分析器

        Args:
            style: 风格预设 (conservative/balanced/aggressive)，空则使用默认配置
            use_yaml: 是否使用 YAML 配置，None 则自动检测
        """
        self._config = None
        self._use_yaml = False
        self._style = style

        # 尝试加载 YAML 配置
        if use_yaml is None:
            self._use_yaml = YAML_CONFIG_AVAILABLE
        elif use_yaml and YAML_CONFIG_AVAILABLE:
            self._use_yaml = True
        elif use_yaml and not YAML_CONFIG_AVAILABLE:
            logger.warning("YAML 配置不可用，回退到默认值")

        if self._use_yaml:
            try:
                # 重新检查模块是否可用
                from analyzer_config.config_loader import get_analyzer_rules

                self._config = get_analyzer_rules(style=style)
                logger.info(
                    f"StockTrendAnalyzer 加载 YAML 配置，风格: {style or 'default'}"
                )
            except Exception as e:
                logger.warning(f"加载 YAML 配置失败，使用默认值: {e}")
                self._use_yaml = False

    def _get_bias_threshold(self) -> float:
        """获取乖离率阈值"""
        if self._use_yaml and self._config:
            return self._config.bias.threshold
        return self.BIAS_THRESHOLD

    def _get_volume_shrink_ratio(self) -> float:
        """获取缩量判断阈值"""
        if self._use_yaml and self._config:
            return self._config.volume.shrink_threshold
        return self.VOLUME_SHRINK_RATIO

    def _get_volume_heavy_ratio(self) -> float:
        """获取放量判断阈值"""
        if self._use_yaml and self._config:
            return self._config.volume.heavy_threshold
        return self.VOLUME_HEAVY_RATIO

    def _get_ma_periods(self) -> List[int]:
        """获取均线周期列表"""
        if self._use_yaml and self._config:
            return self._config.ma.periods
        return [5, 10, 20, 60]

    def _get_rsi_config(self) -> Tuple[float, float, List[int]]:
        """获取 RSI 配置"""
        if self._use_yaml and self._config:
            return (
                self._config.rsi.overbought,
                self._config.rsi.oversold,
                self._config.rsi.periods,
            )
        return (
            self.RSI_OVERBOUGHT,
            self.RSI_OVERSOLD,
            [self.RSI_SHORT, self.RSI_MID, self.RSI_LONG],
        )

    def _get_macd_config(self) -> Tuple[int, int, int]:
        """获取 MACD 配置"""
        if self._use_yaml and self._config:
            return (
                self._config.macd.fast,
                self._config.macd.slow,
                self._config.macd.signal,
            )
        return self.MACD_FAST, self.MACD_SLOW, self.MACD_SIGNAL

    def _get_risk_limits(self) -> Tuple[float, float]:
        """获取仓位风控参数 (max_position_pct, max_single_position)"""
        if self._use_yaml and self._config:
            return (
                self._config.risk.max_position_pct,
                self._config.risk.max_single_position,
            )
        return 30.0, 20.0

    def analyze(
        self, df: pd.DataFrame, code: str, intraday_df: Optional[pd.DataFrame] = None
    ) -> TrendAnalysisResult:
        """
        分析股票趋势

        Args:
            df: 包含 OHLCV 数据的 DataFrame
            code: 股票代码

        Returns:
            TrendAnalysisResult 分析结果
        """
        result = TrendAnalysisResult(code=code)

        if df is None or df.empty or len(df) < 20:
            logger.warning(f"{code} 数据不足，无法进行趋势分析")
            result.risk_factors.append("数据不足，无法完成分析")
            return result

        # 确保数据按日期排序
        df = df.sort_values("date").reset_index(drop=True)

        # 计算均线
        df = self._calculate_mas(df)

        # 计算 MACD 和 RSI
        df = self._calculate_macd(df)
        df = self._calculate_rsi(df)
        df = self._calculate_atr(df)
        df = self._calculate_bollinger(df)
        df = self._calculate_kdj(df)
        df = self._calculate_obv(df)

        # 获取最新数据
        latest = df.iloc[-1]
        result.current_price = float(latest["close"])
        result.ma5 = float(latest["MA5"])
        result.ma10 = float(latest["MA10"])
        result.ma20 = float(latest["MA20"])
        result.ma60 = float(latest.get("MA60", 0))
        result.atr_14 = float(latest.get("ATR_14", 0.0))
        result.boll_mid = float(latest.get("BOLL_MID", 0.0))
        result.boll_upper = float(latest.get("BOLL_UPPER", 0.0))
        result.boll_lower = float(latest.get("BOLL_LOWER", 0.0))
        result.k_value = float(latest.get("K", 50.0))
        result.d_value = float(latest.get("D", 50.0))
        result.j_value = float(latest.get("J", 50.0))
        result.obv_value = float(latest.get("OBV", 0.0))

        # 1. 趋势判断
        self._analyze_trend(df, result)

        # 2. 乖离率计算
        self._calculate_bias(result)

        # 3. 量能分析
        self._analyze_volume(df, result)

        # 4. 支撑压力分析
        self._analyze_support_resistance(df, result)

        # 5. MACD 分析
        self._analyze_macd(df, result)
        self._estimate_signal_age(df, result)

        # 6. RSI 分析
        self._analyze_rsi(df, result)

        # 7. 布林带分析
        self._analyze_bollinger(result)

        # 8. KDJ 分析
        self._analyze_kdj(df, result)

        # 9. OBV 分析
        self._analyze_obv(df, result)

        # 9. 生成买入信号
        self._generate_signal(result)

        # 9. 多周期共振评估（日线 + 30分钟）
        self._evaluate_multi_timeframe(result, intraday_df)

        # 9. 资金流向分析
        self._analyze_main_fund_flow(df, result)
        self._analyze_northbound_flow(df, result)

        # 10. 多信号共振过滤
        self._apply_resonance_filter(result)

        # 11. 信号衰减过滤
        self._apply_signal_decay(result)

        # 12. 生成交易操作清单
        self._build_trade_plan(result)

        # 12. 生成信号证据（如果可用）
        if EVIDENCE_AVAILABLE and generate_signal_evidence is not None:
            try:
                evidence_summary = generate_signal_evidence(
                    trend_status=result.trend_status.value,
                    ma5=result.ma5,
                    ma10=result.ma10,
                    ma20=result.ma20,
                    current_price=result.current_price,
                    bias_ma5=result.bias_ma5,
                    volume_status=result.volume_status.value,
                    volume_ratio_5d=result.volume_ratio_5d,
                    support_ma5=result.support_ma5,
                    support_ma10=result.support_ma10,
                    macd_status=result.macd_status.value,
                    rsi_status=result.rsi_status.value,
                )
                result.signal_evidence = evidence_summary.to_dict()
            except Exception as e:
                logger.warning(f"生成信号证据失败: {e}")
                result.signal_evidence = {"error": str(e)}

        # 13. 添加行业/风格标签
        self.enrich_with_sector_tags(result)

        return result

    def enrich_with_sector_tags(
        self, result: TrendAnalysisResult
    ) -> TrendAnalysisResult:
        """
        为分析结果添加行业/风格标签

        尝试从 IndustryTagger 获取标签（如果可用）

        Args:
            result: 分析结果

        Returns:
            更新后的分析结果
        """
        try:
            from tags.industry_tagger import IndustryTagger

            tagger = IndustryTagger()
            tags = tagger.get_stock_tags(result.code)
            if hasattr(tags, "to_dict"):
                tags_dict = tags.to_dict()
            elif isinstance(tags, dict):
                tags_dict = tags
            else:
                tags_dict = {"raw": str(tags)}

            result.sector_tags = tags_dict

            logger.debug(f"为 {result.code} 添加标签: {result.sector_tags}")
        except ImportError:
            logger.debug("IndustryTagger 不可用，跳过标签添加")
            result.sector_tags = {"industry": "未知", "concepts": [], "style": "未分类"}
        except Exception as e:
            logger.warning(f"获取标签失败: {e}")
            result.sector_tags = {"error": str(e)}

        return result

    def _calculate_mas(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算均线"""
        df = df.copy()
        df["MA5"] = df["close"].rolling(window=5).mean()
        df["MA10"] = df["close"].rolling(window=10).mean()
        df["MA20"] = df["close"].rolling(window=20).mean()
        if len(df) >= 60:
            df["MA60"] = df["close"].rolling(window=60).mean()
        else:
            df["MA60"] = df["MA20"]  # 数据不足时使用 MA20 替代
        return df

    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 MACD 指标

        公式：
        - EMA(12)：12日指数移动平均
        - EMA(26)：26日指数移动平均
        - DIF = EMA(12) - EMA(26)
        - DEA = EMA(DIF, 9)
        - MACD = (DIF - DEA) * 2
        """
        df = df.copy()

        # 获取 MACD 配置
        macd_fast, macd_slow, macd_signal = self._get_macd_config()

        # 计算快慢线 EMA
        ema_fast = df["close"].ewm(span=macd_fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=macd_slow, adjust=False).mean()

        # 计算快线 DIF
        df["MACD_DIF"] = ema_fast - ema_slow

        # 计算信号线 DEA
        df["MACD_DEA"] = df["MACD_DIF"].ewm(span=macd_signal, adjust=False).mean()

        # 计算柱状图
        df["MACD_BAR"] = (df["MACD_DIF"] - df["MACD_DEA"]) * 2

        return df

    def _calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 RSI 指标

        公式：
        - RS = 平均上涨幅度 / 平均下跌幅度
        - RSI = 100 - (100 / (1 + RS))
        """
        df = df.copy()

        # 获取 RSI 配置
        rsi_overbought, rsi_oversold, rsi_periods = self._get_rsi_config()

        for period in rsi_periods:
            # 计算价格变化
            delta = df["close"].diff()

            # 分离上涨和下跌
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # 计算平均涨跌幅
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()

            # 计算 RS 和 RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            # 填充 NaN 值
            rsi = rsi.fillna(50)  # 默认中性值

            # 添加到 DataFrame
            col_name = f"RSI_{period}"
            df[col_name] = rsi

        return df

    def _calculate_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 ATR(14) 指标"""
        df = df.copy()

        high_low = df["high"] - df["low"]
        high_prev_close = (df["high"] - df["close"].shift(1)).abs()
        low_prev_close = (df["low"] - df["close"].shift(1)).abs()

        true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(
            axis=1
        )
        df["ATR_14"] = true_range.rolling(window=self.ATR_PERIOD).mean().fillna(0.0)
        return df

    def _calculate_bollinger(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算布林带指标"""
        df = df.copy()
        mid = df["close"].rolling(window=self.BOLL_PERIOD).mean()
        std = df["close"].rolling(window=self.BOLL_PERIOD).std()

        df["BOLL_MID"] = mid.fillna(df["close"])
        df["BOLL_UPPER"] = (mid + self.BOLL_STD * std).fillna(df["close"])
        df["BOLL_LOWER"] = (mid - self.BOLL_STD * std).fillna(df["close"])
        return df

    def _calculate_kdj(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 KDJ 指标（9,3,3）"""
        df = df.copy()
        low_n = df["low"].rolling(window=9, min_periods=1).min()
        high_n = df["high"].rolling(window=9, min_periods=1).max()
        rsv = ((df["close"] - low_n) / (high_n - low_n + 1e-9) * 100).fillna(50)

        df["K"] = rsv.ewm(alpha=1 / 3, adjust=False).mean()
        df["D"] = df["K"].ewm(alpha=1 / 3, adjust=False).mean()
        df["J"] = 3 * df["K"] - 2 * df["D"]
        return df

    def _calculate_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 OBV 指标。"""
        df = df.copy()
        close_diff = df["close"].diff().fillna(0)
        direction = np.where(close_diff > 0, 1, np.where(close_diff < 0, -1, 0))
        df["OBV"] = (df["volume"] * direction).cumsum()
        return df

    def _analyze_bollinger(self, result: TrendAnalysisResult) -> None:
        """布林带压力/支撑与突破判断"""
        price = result.current_price
        if result.boll_upper <= 0 or result.boll_lower <= 0:
            result.boll_position = "中轨附近"
            return

        band_width = max(result.boll_upper - result.boll_lower, 1e-6)
        if price > result.boll_upper:
            result.boll_position = "上轨突破"
        elif price >= result.boll_upper - band_width * 0.1:
            result.boll_position = "上轨压力"
        elif price < result.boll_lower:
            result.boll_position = "下轨跌破"
        elif price <= result.boll_lower + band_width * 0.1:
            result.boll_position = "下轨支撑"
        else:
            result.boll_position = "中轨附近"

    def _analyze_kdj(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """KDJ 金叉死叉和超买超卖判断"""
        if len(df) < 2:
            result.kdj_status = "中性"
            return

        prev = df.iloc[-2]
        curr_k = result.k_value
        curr_d = result.d_value

        is_golden = (
            float(prev.get("K", 50)) <= float(prev.get("D", 50)) and curr_k > curr_d
        )
        is_death = (
            float(prev.get("K", 50)) >= float(prev.get("D", 50)) and curr_k < curr_d
        )

        if is_golden and curr_k < 30:
            result.kdj_status = "低位金叉"
        elif is_golden:
            result.kdj_status = "金叉"
        elif is_death and curr_k > 70:
            result.kdj_status = "高位死叉"
        elif is_death:
            result.kdj_status = "死叉"
        elif curr_k > 80 and curr_d > 80:
            result.kdj_status = "超买"
        elif curr_k < 20 and curr_d < 20:
            result.kdj_status = "超卖"
        else:
            result.kdj_status = "中性"

    def _analyze_obv(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """OBV 趋势与价格关系。"""
        if len(df) < 6:
            result.obv_trend = "中性"
            return

        obv_now = float(df["OBV"].iloc[-1])
        obv_prev = float(df["OBV"].iloc[-6])
        price_now = float(df["close"].iloc[-1])
        price_prev = float(df["close"].iloc[-6])

        obv_up = obv_now > obv_prev
        price_up = price_now > price_prev

        if obv_up and price_up:
            result.obv_trend = "量价齐升"
        elif obv_up and not price_up:
            result.obv_trend = "量增价弱(潜在背离)"
        elif not obv_up and price_up:
            result.obv_trend = "价升量弱(顶部风险)"
        else:
            result.obv_trend = "量价齐弱"

    def _build_trade_plan(self, result: TrendAnalysisResult) -> None:
        """构建交易操作清单：买入/止损/目标/仓位/盈亏比"""
        result.entry_price = result.current_price

        atr_value = max(result.atr_14, 0.0)
        stop_distance = atr_value * self.ATR_STOP_MULTIPLIER
        target_distance = atr_value * self.TARGET_PROFIT_MULTIPLIER

        if stop_distance <= 0:
            stop_distance = result.current_price * 0.03
        if target_distance <= 0:
            target_distance = result.current_price * 0.06

        result.stop_loss_price = max(0.0, result.current_price - stop_distance)
        result.target_price = result.current_price + target_distance
        result.atr_stop_loss = stop_distance

        max_position_pct, max_single_position = self._get_risk_limits()
        signal_based_position = min(float(result.signal_score) / 4.0, 25.0)
        result.recommended_position_pct = min(
            signal_based_position, max_position_pct, max_single_position
        )

        loss = max(result.entry_price - result.stop_loss_price, 0.01)
        gain = max(result.target_price - result.entry_price, 0.0)
        result.risk_reward_ratio = round(gain / loss, 2)

    def _evaluate_multi_timeframe(
        self, result: TrendAnalysisResult, intraday_df: Optional[pd.DataFrame]
    ) -> None:
        """评估日线与30分钟级别是否共振。"""
        if intraday_df is None or intraday_df.empty or len(intraday_df) < 20:
            result.timeframe_alignment = False
            result.timeframe_notes.append("无30分钟数据，未进行多周期共振验证")
            return

        data = intraday_df.sort_values("date").reset_index(drop=True).copy()
        data["MA5"] = data["close"].rolling(window=5).mean()
        data["MA10"] = data["close"].rolling(window=10).mean()
        data["MA20"] = data["close"].rolling(window=20).mean()
        latest = data.iloc[-1]

        intraday_bull = (
            float(latest["MA5"]) > float(latest["MA10"]) > float(latest["MA20"])
        )
        daily_bull = result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL]

        result.timeframe_alignment = intraday_bull and daily_bull
        if result.timeframe_alignment:
            result.timeframe_notes.append("日线与30分钟级别同向多头，共振成立")
            result.signal_reasons.append("✅ 多周期共振（日线+30分钟）")
            result.signal_score = min(100, result.signal_score + 5)
        else:
            result.timeframe_notes.append("多周期未共振，短线方向与日线不一致")
            result.risk_factors.append("⚠️ 多周期未共振，降低仓位")

    def _analyze_main_fund_flow(
        self, df: pd.DataFrame, result: TrendAnalysisResult
    ) -> None:
        """主力资金流向：支持多种列名自动识别。"""
        flow_candidates = [
            "main_fund_net_inflow",
            "main_net_inflow",
            "主力净流入",
            "主力净额",
        ]
        ratio_candidates = [
            "main_fund_inflow_ratio",
            "main_inflow_ratio",
            "主力净占比",
            "主力净流入占比",
        ]

        flow_col = next((c for c in flow_candidates if c in df.columns), None)
        ratio_col = next((c for c in ratio_candidates if c in df.columns), None)

        if flow_col is not None:
            result.main_fund_net_inflow = float(df[flow_col].iloc[-1])
        if ratio_col is not None:
            result.main_fund_inflow_ratio = float(df[ratio_col].iloc[-1])

        if flow_col is not None and result.main_fund_net_inflow > 0:
            result.signal_reasons.append("✅ 主力资金净流入")
        elif flow_col is not None and result.main_fund_net_inflow < 0:
            result.risk_factors.append("⚠️ 主力资金净流出")

    def _analyze_northbound_flow(
        self, df: pd.DataFrame, result: TrendAnalysisResult
    ) -> None:
        """北向资金追踪：支持多种列名自动识别。"""
        candidates = [
            "northbound_net_inflow",
            "northbound_net",
            "北向净流入",
            "北向资金净买额",
        ]
        col = next((c for c in candidates if c in df.columns), None)
        if col is None:
            return

        result.northbound_net_inflow = float(df[col].iloc[-1])
        if result.northbound_net_inflow > 0:
            result.signal_reasons.append("✅ 北向资金净流入")
        elif result.northbound_net_inflow < 0:
            result.risk_factors.append("⚠️ 北向资金净流出")

    def _apply_resonance_filter(self, result: TrendAnalysisResult) -> None:
        """多信号共振过滤：至少 3 个独立信号同向。"""
        signals = [
            result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL],
            result.volume_status
            in [VolumeStatus.SHRINK_VOLUME_DOWN, VolumeStatus.HEAVY_VOLUME_UP],
            result.macd_status
            in [
                MACDStatus.GOLDEN_CROSS_ZERO,
                MACDStatus.GOLDEN_CROSS,
                MACDStatus.BULLISH,
            ],
            result.rsi_status
            in [RSIStatus.STRONG_BUY, RSIStatus.NEUTRAL, RSIStatus.OVERSOLD],
            result.timeframe_alignment,
            result.main_fund_net_inflow > 0,
            result.northbound_net_inflow > 0,
        ]
        count = sum(1 for x in signals if x)
        result.resonance_count = count
        result.resonance_passed = count >= 3

        if not result.resonance_passed:
            result.risk_factors.append(f"⚠️ 多信号共振不足（{count}/3）")
            if result.buy_signal == BuySignal.STRONG_BUY:
                result.buy_signal = BuySignal.BUY
            elif result.buy_signal == BuySignal.BUY:
                result.buy_signal = BuySignal.HOLD

    def _estimate_signal_age(
        self, df: pd.DataFrame, result: TrendAnalysisResult
    ) -> None:
        """估算最近一次 MACD 金叉距今天数。"""
        if len(df) < 2 or "MACD_DIF" not in df.columns or "MACD_DEA" not in df.columns:
            result.signal_age_days = 999
            return

        cross = (df["MACD_DIF"].shift(1) <= df["MACD_DEA"].shift(1)) & (
            df["MACD_DIF"] > df["MACD_DEA"]
        )
        cross_idx = np.where(cross.fillna(False))[0]
        if len(cross_idx) == 0:
            result.signal_age_days = 999
            return

        result.signal_age_days = int(len(df) - 1 - cross_idx[-1])

    def _apply_signal_decay(self, result: TrendAnalysisResult) -> None:
        """信号衰减：金叉后超过 N 天，买入信号降级。"""
        result.signal_valid = result.signal_age_days <= self.SIGNAL_EXPIRY_DAYS
        if result.signal_valid:
            return

        result.risk_factors.append(
            f"⚠️ 信号已衰减（距最近金叉 {result.signal_age_days} 天，超过 {self.SIGNAL_EXPIRY_DAYS} 天）"
        )
        if result.buy_signal == BuySignal.STRONG_BUY:
            result.buy_signal = BuySignal.BUY
        elif result.buy_signal == BuySignal.BUY:
            result.buy_signal = BuySignal.HOLD

    def _analyze_trend(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        分析趋势状态

        核心逻辑：判断均线排列和趋势强度
        """
        ma5, ma10, ma20 = result.ma5, result.ma10, result.ma20

        # 判断均线排列
        if ma5 > ma10 > ma20:
            # 检查间距是否在扩大（强势）
            prev = df.iloc[-5] if len(df) >= 5 else df.iloc[-1]
            prev_spread = (
                (prev["MA5"] - prev["MA20"]) / prev["MA20"] * 100
                if prev["MA20"] > 0
                else 0
            )
            curr_spread = (ma5 - ma20) / ma20 * 100 if ma20 > 0 else 0

            if curr_spread > prev_spread and curr_spread > 5:
                result.trend_status = TrendStatus.STRONG_BULL
                result.ma_alignment = "强势多头排列，均线发散上行"
                result.trend_strength = 90
            else:
                result.trend_status = TrendStatus.BULL
                result.ma_alignment = "多头排列 MA5>MA10>MA20"
                result.trend_strength = 75

        elif ma5 > ma10 and ma10 <= ma20:
            result.trend_status = TrendStatus.WEAK_BULL
            result.ma_alignment = "弱势多头，MA5>MA10 但 MA10≤MA20"
            result.trend_strength = 55

        elif ma5 < ma10 < ma20:
            prev = df.iloc[-5] if len(df) >= 5 else df.iloc[-1]
            prev_spread = (
                (prev["MA20"] - prev["MA5"]) / prev["MA5"] * 100
                if prev["MA5"] > 0
                else 0
            )
            curr_spread = (ma20 - ma5) / ma5 * 100 if ma5 > 0 else 0

            if curr_spread > prev_spread and curr_spread > 5:
                result.trend_status = TrendStatus.STRONG_BEAR
                result.ma_alignment = "强势空头排列，均线发散下行"
                result.trend_strength = 10
            else:
                result.trend_status = TrendStatus.BEAR
                result.ma_alignment = "空头排列 MA5<MA10<MA20"
                result.trend_strength = 25

        elif ma5 < ma10 and ma10 >= ma20:
            result.trend_status = TrendStatus.WEAK_BEAR
            result.ma_alignment = "弱势空头，MA5<MA10 但 MA10≥MA20"
            result.trend_strength = 40

        else:
            result.trend_status = TrendStatus.CONSOLIDATION
            result.ma_alignment = "均线缠绕，趋势不明"
            result.trend_strength = 50

    def _calculate_bias(self, result: TrendAnalysisResult) -> None:
        """
        计算乖离率

        乖离率 = (现价 - 均线) / 均线 * 100%

        严进策略：乖离率超过 5% 不追高
        """
        price = result.current_price

        if result.ma5 > 0:
            result.bias_ma5 = (price - result.ma5) / result.ma5 * 100
        if result.ma10 > 0:
            result.bias_ma10 = (price - result.ma10) / result.ma10 * 100
        if result.ma20 > 0:
            result.bias_ma20 = (price - result.ma20) / result.ma20 * 100

    def _analyze_volume(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        分析量能

        偏好：缩量回调 > 放量上涨 > 缩量上涨 > 放量下跌
        """
        if len(df) < 5:
            return

        latest = df.iloc[-1]
        vol_5d_avg = df["volume"].iloc[-6:-1].mean()

        if vol_5d_avg > 0:
            result.volume_ratio_5d = float(latest["volume"]) / vol_5d_avg

        # 判断价格变化
        prev_close = df.iloc[-2]["close"]
        price_change = (latest["close"] - prev_close) / prev_close * 100

        # 获取量能配置
        volume_heavy = self._get_volume_heavy_ratio()
        volume_shrink = self._get_volume_shrink_ratio()

        # 量能状态判断
        if result.volume_ratio_5d >= volume_heavy:
            if price_change > 0:
                result.volume_status = VolumeStatus.HEAVY_VOLUME_UP
                result.volume_trend = "放量上涨，多头力量强劲"
            else:
                result.volume_status = VolumeStatus.HEAVY_VOLUME_DOWN
                result.volume_trend = "放量下跌，注意风险"
        elif result.volume_ratio_5d <= volume_shrink:
            if price_change > 0:
                result.volume_status = VolumeStatus.SHRINK_VOLUME_UP
                result.volume_trend = "缩量上涨，上攻动能不足"
            else:
                result.volume_status = VolumeStatus.SHRINK_VOLUME_DOWN
                result.volume_trend = "缩量回调，洗盘特征明显（好）"
        else:
            result.volume_status = VolumeStatus.NORMAL
            result.volume_trend = "量能正常"

    def _analyze_support_resistance(
        self, df: pd.DataFrame, result: TrendAnalysisResult
    ) -> None:
        """
        分析支撑压力位

        买点偏好：回踩 MA5/MA10 获得支撑
        """
        price = result.current_price

        # 检查是否在 MA5 附近获得支撑
        if result.ma5 > 0:
            ma5_distance = abs(price - result.ma5) / result.ma5
            if ma5_distance <= self.MA_SUPPORT_TOLERANCE and price >= result.ma5:
                result.support_ma5 = True
                result.support_levels.append(result.ma5)

        # 检查是否在 MA10 附近获得支撑
        if result.ma10 > 0:
            ma10_distance = abs(price - result.ma10) / result.ma10
            if ma10_distance <= self.MA_SUPPORT_TOLERANCE and price >= result.ma10:
                result.support_ma10 = True
                if result.ma10 not in result.support_levels:
                    result.support_levels.append(result.ma10)

        # MA20 作为重要支撑
        if result.ma20 > 0 and price >= result.ma20:
            result.support_levels.append(result.ma20)

        # 近期高点作为压力
        if len(df) >= 20:
            recent_high = df["high"].iloc[-20:].max()
            if recent_high > price:
                result.resistance_levels.append(recent_high)

    def _analyze_macd(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        分析 MACD 指标

        核心信号：
        - 零轴上金叉：最强买入信号
        - 金叉：DIF 上穿 DEA
        - 死叉：DIF 下穿 DEA
        """
        if len(df) < self.MACD_SLOW:
            result.macd_signal = "数据不足"
            return

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 获取 MACD 数据
        result.macd_dif = float(latest["MACD_DIF"])
        result.macd_dea = float(latest["MACD_DEA"])
        result.macd_bar = float(latest["MACD_BAR"])

        # 判断金叉死叉
        prev_dif_dea = prev["MACD_DIF"] - prev["MACD_DEA"]
        curr_dif_dea = result.macd_dif - result.macd_dea

        # 金叉：DIF 上穿 DEA
        is_golden_cross = prev_dif_dea <= 0 and curr_dif_dea > 0

        # 死叉：DIF 下穿 DEA
        is_death_cross = prev_dif_dea >= 0 and curr_dif_dea < 0

        # 零轴穿越
        prev_zero = prev["MACD_DIF"]
        curr_zero = result.macd_dif
        is_crossing_up = prev_zero <= 0 and curr_zero > 0
        is_crossing_down = prev_zero >= 0 and curr_zero < 0

        # 判断 MACD 状态
        if is_golden_cross and curr_zero > 0:
            result.macd_status = MACDStatus.GOLDEN_CROSS_ZERO
            result.macd_signal = "⭐ 零轴上金叉，强烈买入信号！"
        elif is_crossing_up:
            result.macd_status = MACDStatus.CROSSING_UP
            result.macd_signal = "⚡ DIF上穿零轴，趋势转强"
        elif is_golden_cross:
            result.macd_status = MACDStatus.GOLDEN_CROSS
            result.macd_signal = "✅ 金叉，趋势向上"
        elif is_death_cross:
            result.macd_status = MACDStatus.DEATH_CROSS
            result.macd_signal = "❌ 死叉，趋势向下"
        elif is_crossing_down:
            result.macd_status = MACDStatus.CROSSING_DOWN
            result.macd_signal = "⚠️ DIF下穿零轴，趋势转弱"
        elif result.macd_dif > 0 and result.macd_dea > 0:
            result.macd_status = MACDStatus.BULLISH
            result.macd_signal = "✓ 多头排列，持续上涨"
        elif result.macd_dif < 0 and result.macd_dea < 0:
            result.macd_status = MACDStatus.BEARISH
            result.macd_signal = "⚠ 空头排列，持续下跌"
        else:
            result.macd_status = MACDStatus.BULLISH
            result.macd_signal = " MACD 中性区域"

    def _analyze_rsi(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        分析 RSI 指标

        核心判断：
        - RSI > 70：超买，谨慎追高
        - RSI < 30：超卖，关注反弹
        - 40-60：中性区域
        """
        # 获取 RSI 配置
        rsi_overbought, rsi_oversold, rsi_periods = self._get_rsi_config()
        rsi_long = rsi_periods[-1] if rsi_periods else 24

        if len(df) < rsi_long:
            result.rsi_signal = "数据不足"
            return

        latest = df.iloc[-1]

        # 获取 RSI 数据 - 使用配置的周期
        rsi_6 = rsi_periods[0] if len(rsi_periods) > 0 else 6
        rsi_12 = rsi_periods[1] if len(rsi_periods) > 1 else 12
        rsi_24 = rsi_periods[2] if len(rsi_periods) > 2 else 24

        result.rsi_6 = float(latest[f"RSI_{rsi_6}"])
        result.rsi_12 = float(latest[f"RSI_{rsi_12}"])
        result.rsi_24 = float(latest[f"RSI_{rsi_24}"])

        # 以中期 RSI 为主进行判断
        rsi_mid = result.rsi_12

        # 判断 RSI 状态
        if rsi_mid > rsi_overbought:
            result.rsi_status = RSIStatus.OVERBOUGHT
            result.rsi_signal = f"⚠️ RSI超买({rsi_mid:.1f}>70)，短期回调风险高"
        elif rsi_mid > 60:
            result.rsi_status = RSIStatus.STRONG_BUY
            result.rsi_signal = f"✅ RSI强势({rsi_mid:.1f})，多头力量充足"
        elif rsi_mid >= 40:
            result.rsi_status = RSIStatus.NEUTRAL
            result.rsi_signal = f" RSI中性({rsi_mid:.1f})，震荡整理中"
        elif rsi_mid >= rsi_oversold:
            result.rsi_status = RSIStatus.WEAK
            result.rsi_signal = f"⚡ RSI弱势({rsi_mid:.1f})，关注反弹"
        else:
            result.rsi_status = RSIStatus.OVERSOLD
            result.rsi_signal = f"⭐ RSI超卖({rsi_mid:.1f}<30)，反弹机会大"

    def _generate_signal(self, result: TrendAnalysisResult) -> None:
        """
        生成买入信号

        综合评分系统：
        - 趋势（30分）：多头排列得分高
        - 乖离率（20分）：接近 MA5 得分高
        - 量能（15分）：缩量回调得分高
        - 支撑（10分）：获得均线支撑得分高
        - MACD（15分）：金叉和多头得分高
        - RSI（10分）：超卖和强势得分高
        """
        score = 0
        reasons = []
        risks = []

        # === 趋势评分（30分）===
        trend_scores = {
            TrendStatus.STRONG_BULL: 30,
            TrendStatus.BULL: 26,
            TrendStatus.WEAK_BULL: 18,
            TrendStatus.CONSOLIDATION: 12,
            TrendStatus.WEAK_BEAR: 8,
            TrendStatus.BEAR: 4,
            TrendStatus.STRONG_BEAR: 0,
        }
        trend_score = trend_scores.get(result.trend_status, 12)
        score += trend_score

        if result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL]:
            reasons.append(f"✅ {result.trend_status.value}，顺势做多")
        elif result.trend_status in [TrendStatus.BEAR, TrendStatus.STRONG_BEAR]:
            risks.append(f"⚠️ {result.trend_status.value}，不宜做多")

        # === 乖离率评分（20分）===
        bias = result.bias_ma5
        if bias < 0:
            # 价格在 MA5 下方（回调中）
            if bias > -3:
                score += 20
                reasons.append(f"✅ 价格略低于MA5({bias:.1f}%)，回踩买点")
            elif bias > -5:
                score += 16
                reasons.append(f"✅ 价格回踩MA5({bias:.1f}%)，观察支撑")
            else:
                score += 8
                risks.append(f"⚠️ 乖离率过大({bias:.1f}%)，可能破位")
        elif bias < 2:
            score += 18
            reasons.append(f"✅ 价格贴近MA5({bias:.1f}%)，介入好时机")
        else:
            # 获取乖离率阈值
            bias_threshold = self._get_bias_threshold()
            if bias < bias_threshold:
                score += 14
                reasons.append(f"⚡ 价格略高于MA5({bias:.1f}%)，可小仓介入")
            else:
                score += 4
                risks.append(
                    f"❌ 乖离率过高({bias:.1f}%>{bias_threshold}%)，严禁追高！"
                )

        # === 量能评分（15分）===
        volume_scores = {
            VolumeStatus.SHRINK_VOLUME_DOWN: 15,  # 缩量回调最佳
            VolumeStatus.HEAVY_VOLUME_UP: 12,  # 放量上涨次之
            VolumeStatus.NORMAL: 10,
            VolumeStatus.SHRINK_VOLUME_UP: 6,  # 无量上涨较差
            VolumeStatus.HEAVY_VOLUME_DOWN: 0,  # 放量下跌最差
        }
        vol_score = volume_scores.get(result.volume_status, 8)
        score += vol_score

        if result.volume_status == VolumeStatus.SHRINK_VOLUME_DOWN:
            reasons.append("✅ 缩量回调，主力洗盘")
        elif result.volume_status == VolumeStatus.HEAVY_VOLUME_DOWN:
            risks.append("⚠️ 放量下跌，注意风险")

        # === 支撑评分（10分）===
        if result.support_ma5:
            score += 5
            reasons.append("✅ MA5支撑有效")
        if result.support_ma10:
            score += 5
            reasons.append("✅ MA10支撑有效")

        # === MACD 评分（15分）===
        macd_scores = {
            MACDStatus.GOLDEN_CROSS_ZERO: 15,  # 零轴上金叉最强
            MACDStatus.GOLDEN_CROSS: 12,  # 金叉
            MACDStatus.CROSSING_UP: 10,  # 上穿零轴
            MACDStatus.BULLISH: 8,  # 多头
            MACDStatus.BEARISH: 2,  # 空头
            MACDStatus.CROSSING_DOWN: 0,  # 下穿零轴
            MACDStatus.DEATH_CROSS: 0,  # 死叉
        }
        macd_score = macd_scores.get(result.macd_status, 5)
        score += macd_score

        if result.macd_status in [
            MACDStatus.GOLDEN_CROSS_ZERO,
            MACDStatus.GOLDEN_CROSS,
        ]:
            reasons.append(f"✅ {result.macd_signal}")
        elif result.macd_status in [MACDStatus.DEATH_CROSS, MACDStatus.CROSSING_DOWN]:
            risks.append(f"⚠️ {result.macd_signal}")
        else:
            reasons.append(result.macd_signal)

        # === RSI 评分（10分）===
        rsi_scores = {
            RSIStatus.OVERSOLD: 10,  # 超卖最佳
            RSIStatus.STRONG_BUY: 8,  # 强势
            RSIStatus.NEUTRAL: 5,  # 中性
            RSIStatus.WEAK: 3,  # 弱势
            RSIStatus.OVERBOUGHT: 0,  # 超买最差
        }
        rsi_score = rsi_scores.get(result.rsi_status, 5)
        score += rsi_score

        if result.rsi_status in [RSIStatus.OVERSOLD, RSIStatus.STRONG_BUY]:
            reasons.append(f"✅ {result.rsi_signal}")
        elif result.rsi_status == RSIStatus.OVERBOUGHT:
            risks.append(f"⚠️ {result.rsi_signal}")
        else:
            reasons.append(result.rsi_signal)

        # === 布林带辅助判断（不直接计分）===
        if result.boll_position == "下轨支撑":
            reasons.append("✅ 布林下轨附近获支撑，关注反弹")
        elif result.boll_position == "上轨突破":
            reasons.append("⚡ 布林上轨突破，动量增强")
        elif result.boll_position == "上轨压力":
            risks.append("⚠️ 接近布林上轨压力，谨防冲高回落")
        elif result.boll_position == "下轨跌破":
            risks.append("⚠️ 跌破布林下轨，短线偏弱")

        # === KDJ 辅助判断（不直接计分）===
        if result.kdj_status in ["低位金叉", "金叉", "超卖"]:
            reasons.append(f"✅ KDJ: {result.kdj_status}")
        elif result.kdj_status in ["高位死叉", "死叉", "超买"]:
            risks.append(f"⚠️ KDJ: {result.kdj_status}")

        # === OBV 辅助判断（不直接计分）===
        if result.obv_trend in ["量价齐升", "量增价弱(潜在背离)"]:
            reasons.append(f"✅ OBV: {result.obv_trend}")
        elif result.obv_trend in ["价升量弱(顶部风险)", "量价齐弱"]:
            risks.append(f"⚠️ OBV: {result.obv_trend}")

        # === 综合判断 ===
        result.signal_score = score
        result.signal_reasons = reasons
        result.risk_factors = risks

        # 生成买入信号（调整阈值以适应新的100分制）
        if score >= 75 and result.trend_status in [
            TrendStatus.STRONG_BULL,
            TrendStatus.BULL,
        ]:
            result.buy_signal = BuySignal.STRONG_BUY
        elif score >= 60 and result.trend_status in [
            TrendStatus.STRONG_BULL,
            TrendStatus.BULL,
            TrendStatus.WEAK_BULL,
        ]:
            result.buy_signal = BuySignal.BUY
        elif score >= 45:
            result.buy_signal = BuySignal.HOLD
        elif score >= 30:
            result.buy_signal = BuySignal.WAIT
        elif result.trend_status in [TrendStatus.BEAR, TrendStatus.STRONG_BEAR]:
            result.buy_signal = BuySignal.STRONG_SELL
        else:
            result.buy_signal = BuySignal.SELL

    def format_analysis(self, result: TrendAnalysisResult) -> str:
        """
        格式化分析结果为文本

        Args:
            result: 分析结果

        Returns:
            格式化的分析文本
        """
        lines = [
            f"=== {result.code} 趋势分析 ===",
            f"",
            f"📊 趋势判断: {result.trend_status.value}",
            f"   均线排列: {result.ma_alignment}",
            f"   趋势强度: {result.trend_strength}/100",
            f"",
            f"📈 均线数据:",
            f"   现价: {result.current_price:.2f}",
            f"   MA5:  {result.ma5:.2f} (乖离 {result.bias_ma5:+.2f}%)",
            f"   MA10: {result.ma10:.2f} (乖离 {result.bias_ma10:+.2f}%)",
            f"   MA20: {result.ma20:.2f} (乖离 {result.bias_ma20:+.2f}%)",
            f"",
            f"📊 量能分析: {result.volume_status.value}",
            f"   量比(vs5日): {result.volume_ratio_5d:.2f}",
            f"   量能趋势: {result.volume_trend}",
            f"   主力净流入: {result.main_fund_net_inflow:.2f}",
            f"   主力净占比: {result.main_fund_inflow_ratio:.2f}%",
            f"   北向净流入: {result.northbound_net_inflow:.2f}",
            f"",
            f"📈 MACD指标: {result.macd_status.value}",
            f"   DIF: {result.macd_dif:.4f}",
            f"   DEA: {result.macd_dea:.4f}",
            f"   MACD: {result.macd_bar:.4f}",
            f"   信号: {result.macd_signal}",
            f"",
            f"📉 布林带:",
            f"   上轨: {result.boll_upper:.2f}",
            f"   中轨: {result.boll_mid:.2f}",
            f"   下轨: {result.boll_lower:.2f}",
            f"   位置: {result.boll_position}",
            f"",
            f"📊 RSI指标: {result.rsi_status.value}",
            f"   RSI(6): {result.rsi_6:.1f}",
            f"   RSI(12): {result.rsi_12:.1f}",
            f"   RSI(24): {result.rsi_24:.1f}",
            f"   信号: {result.rsi_signal}",
            f"",
            f"📈 KDJ指标:",
            f"   K: {result.k_value:.1f}",
            f"   D: {result.d_value:.1f}",
            f"   J: {result.j_value:.1f}",
            f"   状态: {result.kdj_status}",
            f"",
            f"📊 OBV指标:",
            f"   OBV: {result.obv_value:.0f}",
            f"   趋势: {result.obv_trend}",
            f"",
            f"🛡️ ATR风控:",
            f"   ATR(14): {result.atr_14:.4f}",
            f"   ATR止损距离: {result.atr_stop_loss:.4f}",
            f"",
            f"🎯 操作建议: {result.buy_signal.value}",
            f"   综合评分: {result.signal_score}/100",
            f"   买入价: {result.entry_price:.2f}",
            f"   止损价: {result.stop_loss_price:.2f}",
            f"   目标价: {result.target_price:.2f}",
            f"   建议仓位: {result.recommended_position_pct:.1f}%",
            f"   风险收益比: 1:{result.risk_reward_ratio:.2f}",
            f"   多周期共振: {'是' if result.timeframe_alignment else '否'}",
            f"   多信号共振: {'通过' if result.resonance_passed else '未通过'} ({result.resonance_count}项)",
            f"   信号衰减: {'有效' if result.signal_valid else '失效'} (信号龄期{result.signal_age_days}天)",
        ]

        if result.timeframe_notes:
            lines.append("")
            lines.append("🧭 多周期评估:")
            for note in result.timeframe_notes:
                lines.append(f"   {note}")

        if result.signal_reasons:
            lines.append(f"")
            lines.append(f"✅ 买入理由:")
            for reason in result.signal_reasons:
                lines.append(f"   {reason}")

        if result.risk_factors:
            lines.append(f"")
            lines.append(f"⚠️ 风险因素:")
            for risk in result.risk_factors:
                lines.append(f"   {risk}")

        return "\n".join(lines)


def analyze_stock(df: pd.DataFrame, code: str) -> TrendAnalysisResult:
    """
    便捷函数：分析单只股票

    Args:
        df: 包含 OHLCV 数据的 DataFrame
        code: 股票代码

    Returns:
        TrendAnalysisResult 分析结果
    """
    analyzer = StockTrendAnalyzer()
    return analyzer.analyze(df, code)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    # 模拟数据测试
    import numpy as np

    dates = pd.date_range(start="2025-01-01", periods=60, freq="D")
    np.random.seed(42)

    # 模拟多头排列的数据
    base_price = 10.0
    prices = [base_price]
    for i in range(59):
        change = np.random.randn() * 0.02 + 0.003  # 轻微上涨趋势
        prices.append(prices[-1] * (1 + change))

    df = pd.DataFrame(
        {
            "date": dates,
            "open": prices,
            "high": [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
            "low": [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
            "close": prices,
            "volume": [np.random.randint(1000000, 5000000) for _ in prices],
        }
    )

    analyzer = StockTrendAnalyzer()
    result = analyzer.analyze(df, "000001")
    print(analyzer.format_analysis(result))
