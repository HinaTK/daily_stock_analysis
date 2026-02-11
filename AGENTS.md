# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-31
**Commit:** (unknown)
**Branch:** (unknown)

## OVERVIEW
本仓库是“股票智能分析系统”：定时拉取行情/情报，结合趋势规则与大模型分析，生成报告并推送到多渠道；支持 GitHub Actions 每工作日 18:00（北京时间）自动运行。

## STRUCTURE
```
./
├── main.py                 # CLI 主入口：调度全流程（个股 + 大盘复盘 + WebUI/定时）
├── analyzer_service.py     # 供 WebUI/Bot 复用的分析服务 API（不依赖 CLI 参数）
├── webui.py                # WebUI 兼容入口（实际实现在 web/）
├── test_env.py             # 环境验证脚本（配置/数据库/数据源/LLM/通知）
├── src/                    # 核心业务：配置/存储/搜索/分析/通知/调度/流水线
├── data_provider/          # 数据源策略层：多数据源 + 故障切换 + 流控/熔断
├── web/                    # 轻量 WebUI：HTTPServer + 路由 + handlers + services + templates
├── bot/                    # 机器人：Webhook/Stream 适配 + 命令分发
└── .github/workflows/      # Actions：每日分析、CI、PR AI 审查等
```

## WHERE TO LOOK
| 任务 | 位置 | 备注 |
|------|------|------|
| 跑一次完整分析 | `main.py` | `python main.py`（可加 `--no-market-review` / `--market-review`） |
| 分析流程编排/并发 | `src/core/pipeline.py` | fetch→存储→增强→趋势→搜索→LLM→通知 |
| 配置/环境变量 | `src/config.py` | `.env` + 环境变量；大量开关/限流/渠道配置 |
| 数据库与断点续传 | `src/storage.py` | SQLite + SQLAlchemy；“今日已有数据则跳过” |
| LLM 调用与返回结构 | `src/analyzer.py` | Gemini 主 + fallback + OpenAI 兼容；决策仪表盘数据结构 |
| 多渠道推送/报表渲染 | `src/notification.py` | 企业微信/飞书/Telegram/邮件/PushPlus/Discord/自定义 |
| 数据源切换/熔断/缓存 | `data_provider/base.py` | DataFetcherManager；标准列名；指标计算 |
| WebUI 路由与安全边界 | `web/router.py` | `/update` 会写 `.env`；默认无鉴权 |
| Bot Webhook 入口与分发 | `bot/handler.py` | 平台适配器→dispatcher→commands |
| GitHub Actions 每日任务 | `.github/workflows/daily_analysis.yml` | secrets/vars 注入；默认关闭筹码分布 |
| PR AI 审查（高风险） | `.github/workflows/pr-review.yml` | `pull_request_target` + secrets；见子规则 |

## CONVENTIONS
- 配置访问用单例：`src/config.py` 的 `get_config()`；数据库用 `src/storage.py` 的 `get_db()`。
- 断点续传默认开启：流水线里会先检查“今日数据是否已存在”，避免重复抓取。
- 流控/反封禁是核心：数据源层有随机 sleep、重试、熔断；Gemini 侧有 request delay 与 retry。

## ANTI-PATTERNS (THIS PROJECT)
- 不要在日志/异常里打印 secrets（包括“前 8 位”这种片段）；PR 审查 workflow 会在敏感场景运行。
- 不要把 WebUI 暴露到公网：`web/` 默认无鉴权，`POST /update` 可改写 `.env`，`GET /analysis` 可触发后台分析。
- 修改 `.github/workflows/` 或 `.github/scripts/` 视为敏感变更：需要额外人工审查（尤其是 `pull_request_target` 相关）。

## UNIQUE STYLES
- 交易理念内置（不追高/均线多头/缩量回踩等）会影响趋势规则与提示文案；相关逻辑集中在 `src/stock_analyzer.py` 和 LLM prompt。
- 同时支持“推送日报汇总”与“单股即时推送”（`SINGLE_STOCK_NOTIFY` / `--single-notify`）。

## COMMANDS
```bash
# 安装依赖
pip install -r requirements.txt

# 运行（本地）
python main.py
python main.py --market-review
python main.py --no-market-review

# WebUI
python main.py --webui
python main.py --webui-only
python webui.py

# 环境自检
python test_env.py

# pytest（配置在 setup.cfg）
pytest -v --tb=short
```

## NOTES
- `main.py` 在“非 GitHub Actions”环境会写入 `http_proxy/https_proxy`（本地开发代理）；排查网络问题先看这里。
- `ENABLE_CHIP_DISTRIBUTION` 在云端（Actions）默认关闭，因为接口不稳定；不要把失败当成核心流程失败。
