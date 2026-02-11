# web/ KNOWLEDGE

## OVERVIEW
轻量 WebUI：基于 `http.server` 的 ThreadingHTTPServer，提供配置页面 + 任务触发/查询接口，同时承载 Bot Webhook。

## WHERE TO LOOK
| 任务 | 位置 | 备注 |
|------|------|------|
| HTTPServer 启动/线程后台运行 | `web/server.py` | WebServer.run()/start_background() |
| 路由与请求分发 | `web/router.py` | GET/POST 分发；`/bot/*` 特殊处理原始 body |
| 页面/API 处理 | `web/handlers.py` | PageHandler/ApiHandler/BotHandler |
| 业务服务 | `web/services.py` | ConfigService（读写 .env）、AnalysisService（后台分析任务） |
| 页面渲染 | `web/templates.py` | HTML 模板（较大文件） |

## CONVENTIONS
- 任务触发走后台线程/执行器：不要在 HTTP handler 里做长耗时分析。
- Bot Webhook 需要原始 body：路由层会保留 `raw_body_bytes`；不要把它当普通 form 表单解析。

## ANTI-PATTERNS
- 不要把 WebUI 暴露到公网：当前无鉴权，`POST /update` 可改写 `.env`，`GET /analysis` 可触发后台分析。
- 不要在模板/日志里回显敏感配置（API Key、Webhook URL、邮箱授权码等）。
