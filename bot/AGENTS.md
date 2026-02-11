# bot/ KNOWLEDGE

## OVERVIEW
机器人子系统：平台适配（Webhook/Stream）+ 命令分发 + 与分析流水线/服务层集成。

## WHERE TO LOOK
| 任务 | 位置 | 备注 |
|------|------|------|
| Webhook 统一入口 | `bot/handler.py` | 平台解析→dispatcher→命令；平台在 `ALL_PLATFORMS` 注册 |
| 命令解析/频率限制/分发 | `bot/dispatcher.py` | RateLimiter + CommandDispatcher |
| 消息/响应数据模型 | `bot/models.py` | BotMessage/BotResponse/WebhookResponse |
| 命令实现 | `bot/commands/` | `/analyze`/`/batch`/`/market` 等 |
| 平台适配器 | `bot/platforms/` | 签名校验、challenge、stream 模式 |

## CONVENTIONS
- 入口统一走 dispatcher：平台适配器只做“验签 + 解包/封包”，不要在平台层直接跑分析。
- 频控是必须能力：默认对单用户做滑动窗口限流（见 `bot/dispatcher.py`）。

## ANTI-PATTERNS
- 不要默认放宽验签：如果 platform secret 未配置，现状可能接受未签名请求；外网部署前必须明确安全策略。
- 不要无限制创建后台线程：命令触发分析时要考虑任务队列/并发上限与任务清理。
