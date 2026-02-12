# -*- coding: utf-8 -*-
"""
===================================
趋势分析扩展 - 结构化信号证据
===================================

功能：
1. 为 TrendAnalysisResult 添加结构化信号证据
2. 支持从 YAML 配置读取规则
3. 提供证据对比表（触发条件 vs 实际值）

使用方式：
    from src.analysis_ext import SignalEvidence, analyze_with_evidence

    # 方法1：使用扩展分析
    result = analyze_with_evidence(df, code)

    # 方法2：为现有结果添加证据
    evidence = generate_signal_evidence(existing_result)
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class EvidenceType(Enum):
    """证据类型"""

    TREND = "trend"  # 趋势证据
    BIAS = "bias"  # 乖离率证据
    VOLUME = "volume"  # 量能证据
    SUPPORT = "support"  # 支撑证据
    MACD = "macd"  # MACD 证据
    RSI = "rsi"  # RSI 证据


@dataclass
class SignalEvidence:
    """信号证据"""

    rule_name: str  # 规则名称
    rule_type: EvidenceType  # 证据类型
    triggered: bool  # 是否触发
    condition: str  # 触发条件描述
    actual_value: float  # 实际值
    threshold: float  # 阈值
    direction: str  # "触发" / "未触发" / "失效"
    weight: float  # 规则权重
    score_contribution: float  # 得分贡献
    invalidation_condition: str = ""  # 失效条件
    risk_note: str = ""  # 风险提示
    opportunity_note: str = ""  # 机会提示

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "rule_type": self.rule_type.value,
            "triggered": self.triggered,
            "condition": self.condition,
            "actual_value": self.actual_value,
            "threshold": self.threshold,
            "direction": self.direction,
            "weight": self.weight,
            "score_contribution": self.score_contribution,
            "invalidation_condition": self.invalidation_condition,
            "risk_note": self.risk_note,
            "opportunity_note": self.opportunity_note,
        }


@dataclass
class EvidenceSummary:
    """证据汇总"""

    total_score: int = 0
    evidence_list: List[SignalEvidence] = field(default_factory=list)
    triggered_count: int = 0
    invalid_count: int = 0
    risk_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score": self.total_score,
            "evidence_count": len(self.evidence_list),
            "triggered_count": self.triggered_count,
            "invalid_count": self.invalid_count,
            "risk_count": self.risk_count,
            "evidence": [e.to_dict() for e in self.evidence_list],
        }


def generate_signal_evidence(
    trend_status: str,
    ma5: float,
    ma10: float,
    ma20: float,
    current_price: float,
    bias_ma5: float,
    volume_status: str,
    volume_ratio_5d: float,
    support_ma5: bool,
    support_ma10: bool,
    macd_status: str,
    rsi_status: str,
    scoring_config: Optional[Dict] = None,
) -> EvidenceSummary:
    """生成结构化信号证据

    Args:
        trend_status: 趋势状态字符串
        ma5/ma10/ma20: 均线数据
        current_price: 当前价格
        bias_ma5: 乖离率
        volume_status: 量能状态
        volume_ratio_5d: 量比
        support_ma5/ma10: 支撑状态
        macd_status: MACD 状态
        rsi_status: RSI 状态
        scoring_config: 评分配置（可选）

    Returns:
        EvidenceSummary: 证据汇总
    """
    # 默认评分配置
    if scoring_config is None:
        scoring_config = {
            "trend": {"weight": 30, "strong_bull": 30, "bull": 26, "weak_bull": 18},
            "bias": {"weight": 20, "optimal_below": 20, "acceptable_below": 16},
            "volume": {"weight": 15, "shrink_down": 15, "heavy_up": 12},
            "support": {"weight": 10, "ma5_support": 5, "ma10_support": 5},
            "macd": {"weight": 15, "golden_cross_zero": 15, "golden_cross": 12},
            "rsi": {"weight": 10, "oversold": 10, "overbought": 0},
        }

    evidence = []
    total_score = 0

    # 1. 趋势证据
    trend_config = scoring_config.get("trend", {})
    if trend_status == "强势多头":
        score = trend_config.get("strong_bull", 30)
        evidence.append(
            SignalEvidence(
                rule_name="ma_alignment",
                rule_type=EvidenceType.TREND,
                triggered=True,
                condition="MA5 > MA10 > MA20 且均线发散",
                actual_value=f"MA5={ma5:.2f}, MA10={ma10:.2f}, MA20={ma20:.2f}",
                threshold="多头排列",
                direction="触发",
                weight=trend_config.get("weight", 30),
                score_contribution=score,
                opportunity_note="趋势强劲，可顺势做多",
            )
        )
        total_score += score
    elif trend_status == "多头排列":
        score = trend_config.get("bull", 26)
        evidence.append(
            SignalEvidence(
                rule_name="ma_alignment",
                rule_type=EvidenceType.TREND,
                triggered=True,
                condition="MA5 > MA10 > MA20",
                actual_value=f"MA5={ma5:.2f}, MA10={ma10:.2f}, MA20={ma20:.2f}",
                threshold="多头排列",
                direction="触发",
                weight=trend_config.get("weight", 30),
                score_contribution=score,
            )
        )
        total_score += score
    elif trend_status in ["弱势多头", "盘整"]:
        score = (
            trend_config.get("weak_bull", 18)
            if trend_status == "弱势多头"
            else trend_config.get("consolidation", 12)
        )
        evidence.append(
            SignalEvidence(
                rule_name="ma_alignment",
                rule_type=EvidenceType.TREND,
                triggered=False,
                condition="MA5 > MA10 > MA20",
                actual_value=f"MA5={ma5:.2f}, MA10={ma10:.2f}, MA20={ma20:.2f}",
                threshold="多头排列",
                direction="未触发最优",
                weight=trend_config.get("weight", 30),
                score_contribution=score,
                opportunity_note="等待均线金叉或回踩支撑",
            )
        )
        total_score += score
    elif trend_status in ["空头排列", "强势空头"]:
        score = 0 if trend_status == "强势空头" else trend_config.get("bear", 4)
        evidence.append(
            SignalEvidence(
                rule_name="ma_alignment",
                rule_type=EvidenceType.TREND,
                triggered=False,
                condition="MA5 > MA10 > MA20",
                actual_value=f"MA5={ma5:.2f}, MA10={ma10:.2f}, MA20={ma20:.2f}",
                threshold="多头排列",
                direction="失效",
                weight=trend_config.get("weight", 30),
                score_contribution=score,
                risk_note="趋势向下，暂不建议买入",
            )
        )
        total_score += score

    # 2. 乖离率证据
    bias_config = scoring_config.get("bias", {})
    if bias_ma5 < 0:
        if bias_ma5 > -3:
            score = bias_config.get("optimal_below", 20)
            evidence.append(
                SignalEvidence(
                    rule_name="bias_ma5",
                    rule_type=EvidenceType.BIAS,
                    triggered=True,
                    condition=f"乖离率 < 0%（价格在MA5下方）",
                    actual_value=f"{bias_ma5:.2f}%",
                    threshold="-3% ~ 0%",
                    direction="触发",
                    weight=bias_config.get("weight", 20),
                    score_contribution=score,
                    opportunity_note="回踩买点，可考虑介入",
                )
            )
            total_score += score
        elif bias_ma5 > -5:
            score = bias_config.get("acceptable_below", 16)
            evidence.append(
                SignalEvidence(
                    rule_name="bias_ma5",
                    rule_type=EvidenceType.BIAS,
                    triggered=True,
                    condition=f"-5% < 乖离率 < 0%",
                    actual_value=f"{bias_ma5:.2f}%",
                    threshold="-5% ~ 0%",
                    direction="触发",
                    weight=bias_config.get("weight", 20),
                    score_contribution=score,
                )
            )
            total_score += score
        else:
            score = bias_config.get("over_threshold", 4)
            evidence.append(
                SignalEvidence(
                    rule_name="bias_ma5",
                    rule_type=EvidenceType.BIAS,
                    triggered=False,
                    condition=f"乖离率 < -5%",
                    actual_value=f"{bias_ma5:.2f}%",
                    threshold="-5%",
                    direction="失效",
                    weight=bias_config.get("weight", 20),
                    score_contribution=score,
                    risk_note="乖离率过大，可能破位",
                )
            )
            total_score += score
    elif bias_ma5 < 2:
        score = 18  # 接近MA5
        evidence.append(
            SignalEvidence(
                rule_name="bias_ma5",
                rule_type=EvidenceType.BIAS,
                triggered=True,
                condition=f"0% < 乖离率 < 2%",
                actual_value=f"{bias_ma5:.2f}%",
                threshold="< 2%",
                direction="触发",
                weight=bias_config.get("weight", 20),
                score_contribution=score,
            )
        )
        total_score += score
    elif bias_ma5 < 5:
        score = bias_config.get("acceptable_above", 14)
        evidence.append(
            SignalEvidence(
                rule_name="bias_ma5",
                rule_type=EvidenceType.BIAS,
                triggered=True,
                condition=f"2% < 乖离率 < 5%",
                actual_value=f"{bias_ma5:.2f}%",
                threshold="< 5%",
                direction="触发",
                weight=bias_config.get("weight", 20),
                score_contribution=score,
            )
        )
        total_score += score
    else:
        score = 4
        evidence.append(
            SignalEvidence(
                rule_name="bias_ma5",
                rule_type=EvidenceType.BIAS,
                triggered=False,
                condition=f"乖离率 > 5%",
                actual_value=f"{bias_ma5:.2f}%",
                threshold="5%",
                direction="失效",
                weight=bias_config.get("weight", 20),
                score_contribution=score,
                risk_note="乖离率过高，严禁追高！",
            )
        )
        total_score += score

    # 3. 量能证据
    vol_config = scoring_config.get("volume", {})
    vol_score_map = {
        "缩量回调": vol_config.get("shrink_down", 15),
        "放量上涨": vol_config.get("heavy_up", 12),
        "量能正常": vol_config.get("normal", 10),
        "缩量上涨": vol_config.get("shrink_up", 6),
        "放量下跌": vol_config.get("heavy_down", 0),
    }
    vol_score = vol_score_map.get(volume_status, 10)
    evidence.append(
        SignalEvidence(
            rule_name="volume_status",
            rule_type=EvidenceType.VOLUME,
            triggered=volume_status in ["缩量回调", "放量上涨"],
            condition=volume_status,
            actual_value=f"量比={volume_ratio_5d:.2f}",
            threshold="缩量回调/放量上涨",
            direction="触发" if volume_status in ["缩量回调", "放量上涨"] else "中性",
            weight=vol_config.get("weight", 15),
            score_contribution=vol_score,
            opportunity_note="量价配合良好" if volume_status == "放量上涨" else "",
            risk_note="无量上涨，持续性存疑" if volume_status == "缩量上涨" else "",
        )
    )
    total_score += vol_score

    # 4. 支撑证据
    supp_config = scoring_config.get("support", {})
    score = 0
    if support_ma5:
        score += supp_config.get("ma5_support", 5)
        evidence.append(
            SignalEvidence(
                rule_name="support_ma5",
                rule_type=EvidenceType.SUPPORT,
                triggered=True,
                condition="价格在 MA5 附近获得支撑",
                actual_value=f"MA5={ma5:.2f}, 现价={current_price:.2f}",
                threshold="价格 >= MA5",
                direction="触发",
                weight=supp_config.get("weight", 10),
                score_contribution=supp_config.get("ma5_support", 5),
            )
        )
    if support_ma10:
        score += supp_config.get("ma10_support", 5)
        evidence.append(
            SignalEvidence(
                rule_name="support_ma10",
                rule_type=EvidenceType.SUPPORT,
                triggered=True,
                condition="价格在 MA10 附近获得支撑",
                actual_value=f"MA10={ma10:.2f}, 现价={current_price:.2f}",
                threshold="价格 >= MA10",
                direction="触发",
                weight=supp_config.get("weight", 10),
                score_contribution=supp_config.get("ma10_support", 5),
            )
        )
    total_score += score

    # 统计
    triggered_count = sum(1 for e in evidence if e.triggered and e.direction == "触发")
    invalid_count = sum(1 for e in evidence if e.direction == "失效")
    risk_count = sum(1 for e in evidence if e.risk_note)

    return EvidenceSummary(
        total_score=total_score,
        evidence_list=evidence,
        triggered_count=triggered_count,
        invalid_count=invalid_count,
        risk_count=risk_count,
    )


def format_evidence_table(evidence_summary: EvidenceSummary) -> str:
    """格式化为 Markdown 表格"""
    lines = [
        "## 信号证据对照表",
        "",
        "| 规则 | 条件 | 实际值 | 状态 | 得分 | 说明 |",
        "|------|------|--------|------|------|------|",
    ]

    for e in evidence_summary.evidence_list:
        status_emoji = (
            "✅"
            if e.triggered and e.direction == "触发"
            else ("⚠️" if e.risk_note else "➖")
        )
        lines.append(
            f"| {e.rule_name} | {e.condition} | {e.actual_value} | {status_emoji} | {e.score_contribution} | {e.risk_note or e.opportunity_note or ''} |"
        )

    lines.extend(
        [
            "",
            f"**总分**: {evidence_summary.total_score} / 100",
            f"**触发**: {evidence_summary.triggered_count} | **失效**: {evidence_summary.invalid_count} | **风险**: {evidence_summary.risk_count}",
        ]
    )

    return "\n".join(lines)


if __name__ == "__main__":
    # 测试
    summary = generate_signal_evidence(
        trend_status="多头排列",
        ma5=10.2,
        ma10=10.0,
        ma20=9.8,
        current_price=10.5,
        bias_ma5=2.9,
        volume_status="缩量回调",
        volume_ratio_5d=0.6,
        support_ma5=True,
        support_ma10=True,
        macd_status="金叉",
        rsi_status="强势",
    )

    print(f"总分: {summary.total_score}")
    print(format_evidence_table(summary))
