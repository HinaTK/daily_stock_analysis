# data_provider/ KNOWLEDGE

## OVERVIEW
数据源策略层：统一日线/实时/筹码接口，支持多数据源、熔断、缓存与防封禁流控。

## WHERE TO LOOK
| 任务 | 位置 | 备注 |
|------|------|------|
| 策略核心与标准列名 | `data_provider/base.py` | BaseFetcher + DataFetcherManager；STANDARD_COLUMNS |
| 统一类型/熔断器 | `data_provider/realtime_types.py` | UnifiedRealtimeQuote/ChipDistribution；circuit breaker |
| 数据源优先级规则 | `data_provider/__init__.py` | Tushare token 会动态提升优先级 |
| AkShare 数据源 | `data_provider/akshare_fetcher.py` | 历史 + 多 realtime 源 + 筹码分布（不稳定点） |
| efinance 数据源 | `data_provider/efinance_fetcher.py` | 默认最高优先级；缓存/熔断/流控较多 |

## CONVENTIONS
- DataFrame 输出必须标准化：`date/open/high/low/close/volume/amount/pct_chg`，并补齐 `ma5/ma10/ma20/volume_ratio`。
- failover 由 manager 负责：Fetcher 抛异常即可；不要在单个 fetcher 内吞掉关键错误。
- “反封禁”优先级高：随机 sleep、退避重试、缓存 TTL、熔断冷却都属于业务需求。

## ANTI-PATTERNS
- 不要在云端默认开启不稳定接口：筹码分布在 Actions 建议关闭（对应 `ENABLE_CHIP_DISTRIBUTION=false`）。
- 不要在数据源层写入全局代理/环境变量（代理属于上层运行环境配置）。
