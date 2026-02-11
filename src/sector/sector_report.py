# -*- coding: utf-8 -*-
"""
===================================
板块报告模板
===================================

功能：
1. 生成板块复盘 Markdown 报告
2. 融入现有 notification.py 报告体系
"""

from typing import List, Dict, Any
from datetime import datetime


def format_sector_report(
    sector_name: str,
    sector_type: str,
    analysis_result: Dict[str, Any],
    include_details: bool = True,
) -> str:
    """生成板块分析报告

    Args:
        sector_name: 板块名称
        sector_type: 板块类型（行业/概念）
        analysis_result: 分析结果字典
        include_details: 是否包含详细分析

    Returns:
        str: Markdown 格式报告
    """
    lines = []

    # 标题
    sector_emoji = "🏭" if sector_type == "行业" else "💡"
    lines.append(f"# {sector_emoji} 板块复盘：{sector_name}")
    lines.append("")

    # 概览
    lines.append("## 一、板块概览")
    lines.append("")

    sector = analysis_result.get("sector", {})
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 涨跌幅 | {sector.get('change_pct', 0):+.2f}% |")
    lines.append(f"| 上涨家数 | {sector.get('up_count', 0)} |")
    lines.append(f"| 下跌家数 | {sector.get('down_count', 0)} |")
    lines.append(f"| 涨停家数 | {sector.get('limit_up_count', 0)} |")
    lines.append(f"| 换手率 | {sector.get('turnover_rate', 0):.2f}% |")
    lines.append(f"| 主力净流入 | {sector.get('main_flow', 0):+.1f}亿 |")
    lines.append(f"| 相对大盘 | {sector.get('relative_strength', 0):+.2f}% |")
    lines.append("")

    # 市场状态
    market_status = analysis_result.get("market_status", "震荡")
    trend_status = analysis_result.get("trend_status", "盘整")
    signal_grade = analysis_result.get("signal_grade", "中性")

    status_emoji = {
        "领涨": "📈",
        "跟涨": "➡️",
        "震荡": "➡️",
        "跟跌": "➡️",
        "领跌": "📉",
    }.get(market_status, "➡️")

    lines.append("## 二、板块状态")
    lines.append("")
    lines.append(f"- **{status_emoji} 市场状态**：{market_status}")
    lines.append(f"- **趋势状态**：{trend_status}")
    lines.append(
        f"- **信号等级**：{signal_grade} ({analysis_result.get('signal_score', 0)}分)"
    )
    lines.append("")

    # 操作建议
    action = analysis_result.get("action_advice", "观望")
    confidence = analysis_result.get("confidence", "中")
    allocation = analysis_result.get("target_allocation", "维持当前")

    action_emoji = {
        "增持": "🟢",
        "持有": "🟡",
        "减仓": "🟠",
        "减持": "🔴",
        "观望": "⚪",
    }.get(action, "🟡")

    lines.append("## 三、操作建议")
    lines.append("")
    lines.append(f"- **{action_emoji} 建议**：{action}")
    lines.append(f"- **置信度**：{confidence}")
    lines.append(f"- **仓位建议**：{allocation}")
    lines.append("")

    # 领涨/领跌股票
    leading = analysis_result.get("leading_stocks", [])[:5]
    if leading:
        lines.append("## 四、领涨标的")
        lines.append("")
        lines.append("| 股票 | 涨幅 | 备注 |")
        lines.append("|------|------|------|")
        for stock in leading:
            lines.append(
                f"| {stock.get('name', stock.get('code', ''))} | {stock.get('change_pct', 0):+.2f}% | {'🔥' if stock.get('is_limit_up') else ''} |"
            )
        lines.append("")

    # 风险与机会
    risks = analysis_result.get("risk_factors", [])
    opportunities = analysis_result.get("opportunities", [])

    if risks or opportunities:
        lines.append("## 五、风险与机会")
        lines.append("")

        if opportunities:
            lines.append("### ✅ 机会提示")
            lines.append("")
            for opp in opportunities:
                lines.append(f"- {opp}")
            lines.append("")

        if risks:
            lines.append("### ⚠️ 风险提示")
            lines.append("")
            for risk in risks:
                lines.append(f"- {risk}")
            lines.append("")

    # 证据对照（可选）
    if include_details:
        evidence = analysis_result.get("signal_evidence", [])
        if evidence:
            lines.append("## 六、信号证据")
            lines.append("")
            lines.append("| 规则 | 条件 | 实际值 | 状态 | 得分 |")
            lines.append("|------|------|--------|------|------|")
            for e in evidence:
                status = "✅" if e.get("triggered") else "⚠️"
                lines.append(
                    f"| {e.get('rule_name', '')} | {e.get('condition', '')} | {e.get('actual_value', '')} | {status} | {e.get('score_contribution', 0)} |"
                )
            lines.append("")

    # 时间戳
    updated_at = analysis_result.get("updated_at", datetime.now().isoformat())
    lines.append(f"---\n*更新时间：{updated_at}*")

    return "\n".join(lines)


def format_portfolio_sector_report(
    portfolio_views: List[Dict[str, Any]], sector_results: Dict[str, Dict[str, Any]]
) -> str:
    """生成自选股+板块联动报告

    Args:
        portfolio_views: 自选股视图列表
        sector_results: 板块分析结果字典 {板块名: 结果}

    Returns:
        str: Markdown 格式报告
    """
    lines = []

    lines.append("# 📊 自选股板块联动视图")
    lines.append("")

    # 按板块分组展示
    sector_groups = {}
    for view in portfolio_views:
        sector_name = view.get("sector_name", "未分类")
        if sector_name not in sector_groups:
            sector_groups[sector_name] = []
        sector_groups[sector_name].append(view)

    for sector_name, stocks in sector_groups.items():
        sector_result = sector_results.get(sector_name, {})
        signal_grade = sector_result.get("signal_grade", "中性")
        sector_change = sector_result.get("sector", {}).get("change_pct", 0)

        grade_emoji = {
            "强看多": "🟢",
            "看多": "🟢",
            "中性": "🟡",
            "看空": "🟠",
            "强看空": "🔴",
        }.get(signal_grade, "🟡")

        lines.append(
            f"## {grade_emoji} {sector_name} ({signal_grade} {sector_change:+.1f}%)"
        )
        lines.append("")

        lines.append("| 股票 | 个股信号 | 相对板块 | 板块影响 |")
        lines.append("|------|----------|----------|----------|")

        for view in stocks:
            stock_signal = view.get("stock_signal", "观望")
            rel_perf = view.get("relative_performance", 0)
            sector_impact = view.get("sector_impact", "中性")

            rel_emoji = "⬆️" if rel_perf > 0 else ("⬇️" if rel_perf < 0 else "➡️")
            impact_emoji = {
                "正向": "🟢",
                "负向": "🔴",
                "中性": "🟡",
            }.get(sector_impact, "🟡")

            lines.append(
                f"| {view.get('stock_name', view.get('stock_code', ''))} | {stock_signal} | {rel_emoji} {rel_perf:+.2f}% | {impact_emoji} {sector_impact} |"
            )

        lines.append("")

    return "\n".join(lines)
