<<<<<<< HEAD
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
=======
# AGENTS.md

本文件定义在本仓库中执行开发、Issue 分析、PR 审查时的统一行为准则。  

## 1. 通用协作原则

- 语言与栈：Python 3.10+，遵循仓库现有架构与目录边界。
- 配置约束：统一使用 `.env`（参见 `.env.example`）。
- 代码质量：优先保证可运行、可回归验证、可追踪（日志/错误信息清晰）。
- 风格约束：
  - 行宽 120
  - `black` + `isort` + `flake8`
  - 关键变更需至少做语法检查（`py_compile`）或对应测试验证。
  - 新增或修改的代码注释必须使用英文。
- Git 约束：
  - 未经明确确认，不执行 `git commit`。
  - commit message 不添加 `Co-Authored-By`。
  - 后续所有 commit message 必须使用英文。

## 2. Issue 分析原则

每个 Issue 必须先回答 3 个问题：

1. 是否合理（Reasonable）
- 是否描述了真实影响（功能错误、数据错误、性能/稳定性问题、体验退化）。
- 是否有可验证证据（日志、截图、复现步骤、版本信息）。
- 是否与项目目标相关（股票分析、数据源、通知、API/WebUI、部署链路）。

2. 是否是 Issue（Valid Issue）
- 属于缺陷/功能缺失/回归/文档错误之一，而非纯咨询或环境误用。
- 能定位到仓库责任边界；若是三方服务波动，也需判断是否需要仓库侧兜底。
- 如果是使用问题，应转为文档改进或 FAQ，而不是代码缺陷。

3. 是否好解决（Solvability）
- 可否稳定复现。
- 依赖是否可控（第三方 API、网络、权限、密钥）。
- 变更范围与风险等级（低/中/高）。
- 是否存在临时缓解方案（降级、兜底、开关、重试、回退策略）。

### Issue 结论模板

- 结论：`成立 / 部分成立 / 不成立`
- 分类：`bug / feature / docs / question / external`
- 优先级：`P0 / P1 / P2 / P3`
- 难度：`easy / medium / hard`
- 建议：`立即修复 / 排期修复 / 文档澄清 / 关闭`

## 3. PR 分析原则

每个 PR 需按以下顺序审查：

1. 必要性（Necessity）
- 是否解决明确问题，或提供明确业务价值。
- 是否避免“为了改而改”的重构。

2. 关联性（Traceability）
- 是否关联对应 Issue（建议必须有：`Fixes #xxx` 或 `Refs #xxx`）。
- 若无 Issue，PR 描述必须给出动机、场景与验收标准。

3. 类型判定（Type）
- 明确标注：`fix / feat / refactor / docs / chore / test`。
- 对“fix/bug”类 PR：必须说明原问题、根因、修复点、回归风险。

4. 描述完整性（Description Completeness）
- 必须包含：
  - 背景与问题
  - 变更范围（改了哪些模块）
  - 验证方式与结果（命令、关键输出）
  - 兼容性与破坏性变更说明（如有）
  - 回滚方案（至少一句）
  - 若为 issue 修复：在 PR description 中显式写明关闭语句（如 `Fixes #241` / `Closes #241`）

5. 合入判定（Merge Readiness）
- 可直接合入（Ready to Merge）条件：
  - 目标明确且必要
  - 有 Issue 或同等质量的问题描述
  - 变更与描述一致，无隐藏副作用
  - 关键验证已通过（语法/测试/关键链路）
  - 无阻断性风险（安全、数据损坏、明显性能回退）
- 不可直接合入（Not Ready）条件：
  - 描述不完整，无法确认动机和影响
  - 无验证证据
  - 引入明显风险且无回滚策略
  - 与仓库方向无关或重复实现

## 4. 交付与发布同步原则

- 功能开发、缺陷修复完成后，必须同步更新文档：
  - `README.md`（用户可见能力、使用方式、配置项变化）
  - `docs/CHANGELOG.md`（版本变更记录、影响范围、兼容性说明）
- 发布语义必须与改动规模匹配，在提交说明中添加对应 tag 标签：
  - `#patch`：修复类、小改动
  - `#minor`：新增可用功能、向后兼容
  - `#major`：破坏性变更或重大架构调整
  - `#skip` / `#none`：明确不触发自动版本标签
- 若改动用于解决已有 issue，PR description 必须声明关闭该 issue（`Fixes #xxx` / `Closes #xxx`），避免修复完成后 issue 悬挂。

## 5. 建议评审输出格式

### Issue 评审输出

- `是否合理`：是/否 + 理由
- `是否是 issue`：是/否 + 理由
- `是否好解决`：是/否 + 难点
- `建议动作`：修复/排期/文档/关闭

### PR 评审输出

- `必要性`：通过/不通过
- `是否有对应 issue`：有/无（编号）
- `PR 类型`：fix/feat/...
- `description 完整性`：完整/不完整（缺失项）
- `是否可直接合入`：可/不可 + 必改项

## 6. 快速检查命令（可选）

```bash
./test.sh syntax
python -m py_compile main.py src/*.py data_provider/*.py
flake8 main.py src/ --max-line-length=120
```
>>>>>>> d49959d7a2a59ba8c7338fa13ef1a4fce7608531
