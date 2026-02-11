# src/ KNOWLEDGE

## OVERVIEW
核心业务代码：配置/存储/数据编排/趋势规则/LLM 分析/通知/定时。

## WHERE TO LOOK
| 任务 | 位置 | 备注 |
|------|------|------|
| 全流程编排 | `src/core/pipeline.py` | StockAnalysisPipeline：线程池并发 + 失败隔离 |
| 配置项来源/默认值 | `src/config.py` | `.env` + env vars；大量“防限流/防封禁”参数 |
| SQLite/ORM/断点续传 | `src/storage.py` | StockDaily 模型；上下文组装给分析器 |
| 趋势规则（非 LLM） | `src/stock_analyzer.py` | MA 排列/形态/量能等；输出 TrendAnalysisResult |
| LLM 适配层 | `src/analyzer.py` | Gemini + fallback；输出 AnalysisResult（决策仪表盘） |
| 情报搜索 | `src/search_service.py` | Tavily/SerpAPI/Bocha；多 Key 轮询 + 故障转移 |
| 多渠道推送 | `src/notification.py` | 渠道检测、分片发送、Markdown 渲染 |
| 大盘复盘 | `src/market_analyzer.py` + `src/core/market_review.py` | 复盘生成与推送 |
| 定时任务 | `src/scheduler.py` | schedule + 优雅退出 |
| 飞书云文档 | `src/feishu_doc.py` | 将报告写入飞书文档 |

## CONVENTIONS
- 优先通过 `get_config()`/`get_db()` 获取共享实例，避免在模块 import 时做重 IO。
- 并发相关逻辑集中在 `src/core/pipeline.py`；扩展时优先复用现有线程池/任务模型。
- “报告类型/单股推送/大盘复盘”是核心开关：尽量用 `ReportType` + Config 字段贯穿。

## ANTI-PATTERNS
- 不要在 `src/` 里引入 `web/` 或 `bot/`（保持核心层可复用）；WebUI/Bot 应调用 `analyzer_service.py` 或 pipeline 公共 API。
- 不要把 secrets 写入 `AnalysisResult.raw_response` 或日志；这类内容会进 artifacts/logs。
