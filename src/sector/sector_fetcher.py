# -*- coding: utf-8 -*-
"""
===================================
板块数据获取模块
===================================

功能：
1. 从 AkShare 获取行业板块列表
2. 从 AkShare 获取概念板块列表
3. 获取板块成分股
4. 计算板块指数（成分股加权均价）
5. 获取板块涨跌排行
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    import akshare as ak
except ImportError:
    ak = None

from .sector_types import (
    SectorIndex,
    SectorType,
    SectorStockStats,
)


logger = logging.getLogger(__name__)


class SectorFetcher:
    """
    板块数据获取器
    """

    def __init__(self):
        """初始化板块获取器"""
        self._industry_list_cache = None
        self._concept_list_cache = None

    def _check_akshare(self) -> bool:
        """检查 AkShare 是否可用"""
        if ak is None:
            logger.warning("AkShare 未安装，无法获取板块数据")
            return False
        return True

    def get_industry_list(self) -> List[Dict[str, str]]:
        """获取行业板块列表"""
        if not self._check_akshare():
            return []

        if self._industry_list_cache is not None:
            return self._industry_list_cache

        try:
            df = ak.stock_board_cons_ths(symbol="行业分类")
            if df is not None and not df.empty:
                result = []
                for _, row in df.iterrows():
                    code = str(row.get("代码", ""))
                    name = row.get("名称", "")
                    if code and name:
                        result.append({"code": code, "name": name})
                self._industry_list_cache = result
                logger.info(f"获取到 {len(result)} 个行业板块")
                return result
        except Exception as e:
            logger.warning(f"获取行业板块列表失败: {e}")

        self._industry_list_cache = []
        return []

    def get_concept_list(self) -> List[Dict[str, str]]:
        """获取概念板块列表"""
        if not self._check_akshare():
            return []

        if self._concept_list_cache is not None:
            return self._concept_list_cache

        try:
            df = ak.stock_board_cons_ths(symbol="概念分类")
            if df is not None and not df.empty:
                result = []
                for _, row in df.iterrows():
                    code = str(row.get("代码", ""))
                    name = row.get("名称", "")
                    if code and name:
                        result.append({"code": code, "name": name})
                self._concept_list_cache = result
                logger.info(f"获取到 {len(result)} 个概念板块")
                return result
        except Exception as e:
            logger.warning(f"获取概念板块列表失败: {e}")

        self._concept_list_cache = []
        return []

    def get_sector_constituents(self, sector_code: str) -> List[str]:
        """获取板块成分股"""
        if not self._check_akshare():
            return []

        try:
            df = ak.stock_board_cons_ths(symbol=sector_code)
            if df is not None and not df.empty:
                codes = []
                for _, row in df.iterrows():
                    code = str(row.get("代码", ""))
                    if "." in code:
                        code = code.split(".")[0]
                    if code and code.isdigit() and len(code) == 6:
                        codes.append(code)
                logger.info(f"板块 {sector_code} 包含 {len(codes)} 只成分股")
                return codes
        except Exception as e:
            logger.warning(f"获取板块 {sector_code} 成分股失败: {e}")

        return []

    def get_sector_index(
        self,
        sector_code: str,
        sector_name: str,
        sector_type: SectorType,
        market_index_change: float = 0.0,
    ) -> Optional[SectorIndex]:
        """获取板块指数数据"""
        if not self._check_akshare():
            return None

        try:
            all_codes = self.get_sector_constituents(sector_code)
            if not all_codes:
                return None

            df = ak.stock_board_cons_ths(symbol=sector_code)
            if df is None or df.empty:
                return None

            up_count = down_count = limit_up_count = limit_down_count = 0
            total_change = 0.0

            for _, row in df.iterrows():
                try:
                    change = float(row.get("涨跌幅", 0) or 0)
                    total_change += change
                    if change > 0:
                        up_count += 1
                    elif change < 0:
                        down_count += 1
                    if change >= 9.9:
                        limit_up_count += 1
                    elif change <= -9.9:
                        limit_down_count += 1
                except:
                    pass

            avg_change = total_change / len(all_codes) if all_codes else 0
            relative_strength = avg_change - market_index_change

            strength_score = 50
            if relative_strength > 5:
                strength_score = min(100, 50 + (relative_strength - 5) * 5)
            elif relative_strength < -5:
                strength_score = max(0, 50 + (relative_strength + 5) * 5)
            else:
                strength_score = 50 + relative_strength * 2

            return SectorIndex(
                sector_code=sector_code,
                sector_name=sector_name,
                sector_type=sector_type,
                change_pct=avg_change,
                up_count=up_count,
                down_count=down_count,
                limit_up_count=limit_up_count,
                limit_down_count=limit_down_count,
                avg_change=avg_change,
                relative_strength=relative_strength,
                strength_score=strength_score,
                stock_count=len(all_codes),
            )

        except Exception as e:
            logger.warning(f"获取板块 {sector_code} 指数失败: {e}")

        return None

    def get_hot_sectors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门板块排行"""
        if not self._check_akshare():
            return []

        try:
            df = ak.stock_board_cons_ths(symbol="行业分类")
            if df is not None and not df.empty:
                result = []
                for _, row in df.iterrows():
                    code = str(row.get("代码", ""))
                    name = row.get("名称", "")
                    try:
                        change = float(row.get("涨跌幅", 0) or 0)
                    except:
                        change = 0
                    if code and name:
                        result.append(
                            {
                                "code": code,
                                "name": name,
                                "change_pct": change,
                                "type": "industry",
                            }
                        )
                result.sort(key=lambda x: x["change_pct"], reverse=True)
                return result[:limit]

        except Exception as e:
            logger.warning(f"获取热门板块排行失败: {e}")

        return []

    def get_leading_stocks(
        self, sector_code: str, limit: int = 5
    ) -> List[SectorStockStats]:
        """获取板块领涨股票"""
        if not self._check_akshare():
            return []

        try:
            df = ak.stock_board_cons_ths(symbol=sector_code)
            if df is not None and not df.empty:
                stocks = []
                for _, row in df.iterrows():
                    try:
                        code = str(row.get("代码", ""))
                        if "." in code:
                            code = code.split(".")[0]
                        if not code or not code.isdigit() or len(code) != 6:
                            continue
                        name = row.get("名称", "")
                        change = float(row.get("涨跌幅", 0) or 0)
                        stocks.append(
                            SectorStockStats(
                                code=code,
                                name=name,
                                change_pct=change,
                                is_limit_up=change >= 9.9,
                                is_leading=True,
                            )
                        )
                    except:
                        pass
                stocks.sort(key=lambda x: x.change_pct, reverse=True)
                return stocks[:limit]
        except Exception as e:
            logger.warning(f"获取板块领涨股票失败: {e}")
        return []
