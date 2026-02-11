# .github/scripts KNOWLEDGE

## OVERVIEW
Actions 辅助脚本目录：会在自动化（含 `pull_request_target`）场景执行，属于高敏感代码。

## WHERE TO LOOK
| 任务 | 位置 | 备注 |
|------|------|------|
| PR AI 审查脚本 | `.github/scripts/ai_review.py` | 读取 PR diff，调用 Gemini/OpenAI 生成评论 |

## CONVENTIONS
- 默认把 PR 内容当“不可信输入”：只读分析 diff，不执行、不 import、不运行 PR 代码。
- 所有日志输出都按“公开可见”处理：不能包含 secrets/令牌/邮箱授权码/Webhook。

## ANTI-PATTERNS
- 不要打印 `*_API_KEY` 的任何子串（即使 8 位也不行）。
- 不要在脚本里提升权限或修改仓库状态（push/tag/release）；只允许对 PR/issue 写评论（若确需）。
