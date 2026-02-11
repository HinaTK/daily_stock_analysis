# -*- coding: utf-8 -*-
"""
===================================
自选股板块联动视图
===================================

功能：
1. 生成自选股+板块联动报告
2. 展示个股在板块中的相对表现
"""

from typing import List, Dict, Any


def generate_portfolio_sector_report(
    portfolio_stocks: List[str],
    stock_data: Dict[str, Dict[str, Any]],
    sector_results: Dict[str, Dict[str, Any]],
) -> str:
    """
    生成自选股板块联动报告

    Args:
        portfolio_stocks: 自选股代码列表
        stock_data: {code: {name, change_pct, signal, ...}}
        sector_results: {sector_name: sector_analysis_result}

    Returns:
        str: Markdown 格式报告
    """
    lines = []
    lines.append("# 📊 自选股板块联动视图")
    lines.append("")

    # 按板块分组
    sector_groups = {}
    for code in portfolio_stocks:
        data = stock_data.get(code, {})
        sectors = data.get("sectors", [])
        for sector in sectors:
            if sector not in sector_groups:
                sector_groups[sector] = []
            sector_groups[sector].append(
                {
                    "code": code,
                    "name": data.get("name", code),
                    "change_pct": data.get("change_pct", 0),
                    "signal": data.get("signal", "观望"),
                }
            )

    for sector_name, stocks in sector_groups.items():
        sector_result = sector_results.get(sector_name, {})
        sector_signal = sector_result.get("signal_grade", "中性")
        sector_change = sector_result.get("sector", {}).get("change_pct", 0)

        emoji = {
            "强看多": "🟢",
            "看多": "🟢",
            "中性": "🟡",
            "看空": "🟠",
            "强看空": "🔴",
        }.get(sector_signal, "🟡")

        lines.append(
            f"## {emoji} {sector_name} ({sector_signal} {sector_change:+.1f}%)"
        )
        lines.append("")
        lines.append("| 股票 | 涨跌幅 | 信号 | 相对板块 | 备注 |")
        lines.append("|------|----------|----------|----------|------|")

        for stock in stocks:
            rel = stock["change_pct"] - sector_change
            rel_emoji = "⬆️" if rel > 0 else ("⬇️" if rel < 0 else "➡️")
            lines.append(
                f"| {stock['name']} | {stock['change_pct']:+.2f}% | {stock['signal']} | {rel_emoji} {rel:+.2f}% | |"
            )

        lines.append("")

    return "\n".join(lines)
