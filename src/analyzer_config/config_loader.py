# -*- coding: utf-8 -*-
"""
===================================
配置加载器
===================================

功能：
1. 从 YAML 文件加载规则配置
2. 支持环境变量覆盖
3. 支持风格预设切换
4. 提供配置热更新接口

使用方式：
    from src.config.config_loader import get_analyzer_rules
    rules = get_analyzer_rules()  # 默认加载 analyzer_rules.yaml
    rules = get_analyzer_rules(style="conservative")  # 加载保守风格
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

import yaml


logger = logging.getLogger(__name__)

# 默认配置文件路径
DEFAULT_RULES_PATH = Path(__file__).parent / "analyzer_rules.yaml"


@dataclass
class MAConfig:
    """均线配置"""

    periods: list = field(default_factory=lambda: [5, 10, 20, 60])


@dataclass
class BiasConfig:
    """乖离率配置"""

    threshold: float = 5.0
    optimal_zone: float = 2.0
    warning_zone: float = 3.0


@dataclass
class VolumeConfig:
    """量能配置"""

    shrink_threshold: float = 0.7
    heavy_threshold: float = 1.5


@dataclass
class MACDConfig:
    """MACD 配置"""

    fast: int = 12
    slow: int = 26
    signal: int = 9


@dataclass
class RSIConfig:
    """RSI 配置"""

    periods: list = field(default_factory=lambda: [6, 12, 24])
    overbought: float = 70.0
    oversold: float = 30.0
    neutral_high: float = 60.0
    neutral_low: float = 40.0


@dataclass
class SupportConfig:
    """支撑配置"""

    tolerance: float = 2.0


@dataclass
class ScoringConfig:
    """评分权重配置"""

    trend: dict = field(default_factory=dict)
    bias: dict = field(default_factory=dict)
    volume: dict = field(default_factory=dict)
    support: dict = field(default_factory=dict)
    macd: dict = field(default_factory=dict)
    rsi: dict = field(default_factory=dict)


@dataclass
class SignalsConfig:
    """信号阈值配置"""

    strong_buy: int = 75
    buy: int = 60
    hold: int = 45
    wait: int = 30
    sell: int = 20
    strong_sell: int = 10


@dataclass
class RiskConfig:
    """风控配置"""

    max_position_pct: float = 30.0
    max_daily_stop_loss: float = 5.0
    max_single_position: float = 20.0


@dataclass
class PresetsConfig:
    """风格预设配置"""

    conservative: dict = field(default_factory=dict)
    balanced: dict = field(default_factory=dict)
    aggressive: dict = field(default_factory=dict)


@dataclass
class AnalyzerRules:
    """规则引擎配置（完整）"""

    ma: MAConfig = field(default_factory=MAConfig)
    bias: BiasConfig = field(default_factory=BiasConfig)
    volume: VolumeConfig = field(default_factory=VolumeConfig)
    macd: MACDConfig = field(default_factory=MACDConfig)
    rsi: RSIConfig = field(default_factory=RSIConfig)
    support: SupportConfig = field(default_factory=SupportConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    signals: SignalsConfig = field(default_factory=SignalsConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    presets: PresetsConfig = field(default_factory=PresetsConfig)


# 全局配置缓存
_cached_rules: Optional[AnalyzerRules] = None
_cached_style: str = ""


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """应用环境变量覆盖

    支持的环境变量：
    - ANALYZER_BIAS_THRESHOLD: 乖离率阈值
    - ANALYZER_RSI_OVERBOUGHT: RSI 超买阈值
    - ANALYZER_RSI_OVERSOLD: RSI 超卖阈值
    - ANALYZER_STYLE: 风格预设 (conservative/balanced/aggressive)
    """
    overrides = {}

    # 乖离率阈值
    bias_threshold = os.getenv("ANALYZER_BIAS_THRESHOLD")
    if bias_threshold:
        try:
            overrides["bias"] = {"threshold": float(bias_threshold)}
            logger.info(f"环境变量覆盖乖离率阈值: {bias_threshold}")
        except ValueError:
            logger.warning(f"无效的乖离率阈值环境变量: {bias_threshold}")

    # RSI 超买
    rsi_overbought = os.getenv("ANALYZER_RSI_OVERBOUGHT")
    if rsi_overbought:
        try:
            if "rsi" not in overrides:
                overrides["rsi"] = {}
            overrides["rsi"]["overbought"] = float(rsi_overbought)
            logger.info(f"环境变量覆盖 RSI 超买阈值: {rsi_overbought}")
        except ValueError:
            logger.warning(f"无效的 RSI 超买阈值环境变量: {rsi_overbought}")

    # RSI 超卖
    rsi_oversold = os.getenv("ANALYZER_RSI_OVERSOLD")
    if rsi_oversold:
        try:
            if "rsi" not in overrides:
                overrides["rsi"] = {}
            overrides["rsi"]["oversold"] = float(rsi_oversold)
            logger.info(f"环境变量覆盖 RSI 超卖阈值: {rsi_oversold}")
        except ValueError:
            logger.warning(f"无效的 RSI 超卖阈值环境变量: {rsi_oversold}")

    # 应用覆盖
    if overrides:
        for section, values in overrides.items():
            if section in config:
                config[section].update(values)

    return config


def _apply_preset(config: Dict[str, Any], style: str) -> Dict[str, Any]:
    """应用风格预设

    Args:
        config: 原始配置
        style: 风格名称 (conservative/balanced/aggressive)

    Returns:
        应用预设后的配置
    """
    if not style or style == "balanced":
        return config

    presets = config.get("presets", {})
    if style not in presets:
        logger.warning(f"未知风格预设: {style}，使用默认配置")
        return config

    preset_values = presets[style]
    logger.info(f"应用风格预设: {style}")

    # 应用预设值到对应配置项
    for key, value in preset_values.items():
        if key in config.get("bias", {}) and key.startswith("bias_threshold"):
            if "bias" not in config:
                config["bias"] = {}
            config["bias"]["threshold"] = value
        elif key in config.get("rsi", {}) and key.startswith("rsi_"):
            if "rsi" not in config:
                config["rsi"] = {}
            config["rsi"][key.replace("rsi_", "")] = value
        elif key in config.get("signals", {}) and key.endswith("threshold"):
            if "signals" not in config:
                config["signals"] = {}
            config["signals"][key.replace("_threshold", "")] = value

    return config


def _dict_to_config(config_dict: Dict[str, Any]) -> AnalyzerRules:
    """将字典转换为 AnalyzerRules 对象

    Args:
        config_dict: 配置字典

    Returns:
        AnalyzerRules: 配置对象
    """
    ma_cfg = MAConfig(**config_dict.get("ma", {}))
    bias_cfg = BiasConfig(**config_dict.get("bias", {}))
    volume_cfg = VolumeConfig(**config_dict.get("volume", {}))
    macd_cfg = MACDConfig(**config_dict.get("macd", {}))
    rsi_cfg = RSIConfig(**config_dict.get("rsi", {}))
    support_cfg = SupportConfig(**config_dict.get("support", {}))
    scoring_cfg = ScoringConfig(**config_dict.get("scoring", {}))
    signals_cfg = SignalsConfig(**config_dict.get("signals", {}))
    risk_cfg = RiskConfig(**config_dict.get("risk", {}))
    presets_cfg = PresetsConfig(**config_dict.get("presets", {}))

    return AnalyzerRules(
        ma=ma_cfg,
        bias=bias_cfg,
        volume=volume_cfg,
        macd=macd_cfg,
        rsi=rsi_cfg,
        support=support_cfg,
        scoring=scoring_cfg,
        signals=signals_cfg,
        risk=risk_cfg,
        presets=presets_cfg,
    )


def get_analyzer_rules(
    rules_path: Optional[str] = None, style: str = "", use_cache: bool = True
) -> AnalyzerRules:
    """获取规则引擎配置

    Args:
        rules_path: 配置文件路径（可选，默认使用 analyzer_rules.yaml）
        style: 风格预设（conservative/balanced/aggressive）
        use_cache: 是否使用缓存（默认 True）

    Returns:
        AnalyzerRules: 规则配置对象

    Example:
        # 默认加载
        rules = get_analyzer_rules()

        # 加载保守风格
        rules = get_analyzer_rules(style="conservative")

        # 强制重新加载
        rules = get_analyzer_rules(use_cache=False)
    """
    global _cached_rules, _cached_style

    # 确定配置文件路径
    if rules_path is None:
        rules_path = os.getenv("ANALYZER_RULES_PATH", str(DEFAULT_RULES_PATH))

    # 确定风格
    if not style:
        style = os.getenv("ANALYZER_STYLE", "balanced")

    # 检查缓存
    if use_cache and _cached_rules is not None and _cached_style == style:
        return _cached_rules

    # 加载配置文件
    path = Path(rules_path)
    if not path.exists():
        logger.warning(f"配置文件不存在: {path}，使用默认配置")
        config_dict = {}
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f) or {}
            logger.info(f"加载配置文件: {path}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            config_dict = {}

    # 应用环境变量覆盖
    config_dict = _apply_env_overrides(config_dict)

    # 应用风格预设
    config_dict = _apply_preset(config_dict, style)

    # 转换为配置对象
    rules = _dict_to_config(config_dict)

    # 更新缓存
    _cached_rules = rules
    _cached_style = style

    return rules


def reset_cache() -> None:
    """重置配置缓存（用于强制重新加载）"""
    global _cached_rules, _cached_style
    _cached_rules = None
    _cached_style = ""
    logger.info("配置缓存已重置")


if __name__ == "__main__":
    # 测试配置加载
    import sys

    logging.basicConfig(level=logging.INFO)

    rules = get_analyzer_rules()
    print(f"乖离率阈值: {rules.bias.threshold}")
    print(f"RSI 超买: {rules.rsi.overbought}")
    print(f"评分权重 - 趋势: {rules.scoring.trend.get('weight', 30)}")
