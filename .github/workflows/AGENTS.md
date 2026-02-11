# .github/workflows KNOWLEDGE

## OVERVIEW
CI 与自动化运行入口；包含每日分析、CI、Docker 发布、以及 PR 自动审查（含 AI）。

## WHERE TO LOOK
| 任务 | 位置 | 备注 |
|------|------|------|
| 每日分析调度 | `.github/workflows/daily_analysis.yml` | cron + 手动模式；注入大量 secrets/vars |
| CI（语法/基础检查） | `.github/workflows/ci.yml` | 依赖安装、lint/compile、基础 smoke |
| PR AI 审查（高风险） | `.github/workflows/pr-review.yml` | `pull_request_target` + 写权限 + secrets |

## CONVENTIONS
- Daily workflow 在 Actions 默认关闭不稳定能力：`ENABLE_CHIP_DISTRIBUTION=false`。
- 变更审查要先做“安全检查”（敏感文件改动时应阻断自动运行）。

## ANTI-PATTERNS
- 避免在 `pull_request_target` 中执行来自 PR 的任意代码或脚本；只使用 default branch 的脚本并对 diff 做只读分析。
- 避免打印 secrets 或其片段（包括“前 8 位”）；GitHub masking 不是保密策略。
