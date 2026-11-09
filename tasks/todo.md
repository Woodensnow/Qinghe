# AI 润色：可接入多种模型的统一接口

现状（2026-11-06 检查）：
- `server/ai_polish.py` 只有本地规则引擎 `polish_text`，长度裁剪逻辑写在函数末尾
- `POST /api/ai/polish` 直接调用 `polish_text`，固定返回 `engine='local'`
- 前端弹窗固定显示「本地 AI 润色引擎」；测试断言 `engine == 'local'`

设计：
- 新模块 `server/polish_providers.py`：
  - `PolishRequest`（text / scene / city / variant / limit）与 `PolishResult`（text / provider / model / fallbackFrom）
  - `PolishProvider` 基类 + `@register('名字')` 注册表；新增提供方 = 写一个类并注册
  - 统一错误：`PolishError` → `ProviderConfigError` / `ProviderTimeout` / `ProviderResponseError`
  - 统一后处理：去掉代码块和包裹引号、空结果视为失败、按场景字数上限裁剪（与本地引擎共用 `clip_text`）
  - 内置提供方：`local`（默认，包装现有引擎）、`openai`（OpenAI 兼容 `/chat/completions`，覆盖 OpenAI / Ollama / DeepSeek / Claude 兼容端点等）、`anthropic`（Claude 原生 Messages API）；HTTP 只用 `urllib`
- 配置：环境变量优先，其次可选 JSON 文件（默认 `server/ai_polish.local.json`，可用 `QINGHE_POLISH_CONFIG` 指定）
  - `QINGHE_POLISH_PROVIDER / _MODEL / _BASE_URL / _TIMEOUT / _FALLBACK / _API_KEY_ENV`
  - 密钥只从环境变量读取（默认 `QINGHE_POLISH_API_KEY`）；配置文件里出现密钥字段直接报配置错误
  - 每次请求读取配置，改配置无需改代码
- 失败策略：外部提供方出错（配置错误、超时、网络、响应异常）默认回退本地引擎，响应带 `fallbackFrom`；`QINGHE_POLISH_FALLBACK=off` 时返回 502/503/504 和中文提示；日志不打印密钥和用户原文
- 对外接口兼容：请求不变，响应保留 `text`、`engine`，新增 `provider`、`model`

计划：
- [x] 阅读现有实现与测试
- [x] `ai_polish.py` 抽出 `clip_text`（行为不变）
- [x] 新建 `polish_providers.py`（抽象、注册表、配置、三个提供方、回退）
- [x] `server.py` 路由改用统一入口，响应加 `provider` / `model`
- [x] 前端弹窗按 `provider` / `model` 显示实际引擎
- [x] `.gitignore` 与打包脚本排除本地配置文件
- [x] 测试：假提供方注册、配置解析与密钥规则、本地桩 HTTP 服务（OpenAI 兼容 / Anthropic）、超时、错误回退、关闭回退时的 HTTP 状态；测试夹具清空 `QINGHE_POLISH_*` 环境变量
- [x] README 配置说明（并同步 docs 中「润色只是规则」的描述）
- [x] 运行全部测试

## 结果（2026-11-06）
- 新增 `server/polish_providers.py`：`local`（默认）/ `openai`（OpenAI 兼容）/ `anthropic`（Claude Messages API），新增提供方 = 一个类 + `@register`
- 润色路由移出全局数据锁，只在校验登录时持锁；反向验证：放回锁内时「慢模型不阻塞」测试失败（等待 5 秒）
- 外部模型失败默认回退本地并返回 `fallbackFrom`；`QINGHE_POLISH_FALLBACK=off` 时返回 502 / 503 / 504
- 全部 64 个测试通过（原 46 + 新增 18）；另用真实服务进程 + 本地桩模型做了端到端检查（本地 / 模型 / 连不上回退三种情况）
- 小变化：`GET /api/ai/polish` 由 404 变为 405
- 未覆盖：没有调用任何真实外部模型；超时是单次网络读写超时，不是整体时限


---

# Transformer 文本编码修复与重训（v4）

问题（2026-11-05 检查）：
- 字符词表仅 116 个，真实地陪文字 51.6% 为未登录字符，文本对打分影响 ≈0.03
- 128 字截断，真实地陪 141–174 字全部被截；合成训练文字最长 93 字
- tensor_graph 与模型 max_length 两处独立设置，易越界

计划：
- [x] matching_data：每个划分独立的中性填充句库（不含兴趣/节奏/服务/城市词），用独立 RNG 生成，标签与原数据完全一致
- [x] matching_model：模型按自身位置编码长度截断；训练时随机把 unknown_rate 比例的字符替换为未登录编号
- [x] wide_* 预设：max_length=256、unknown_rate=0.15
- [x] 备份 v3 模型到 matching_v3.pt，refine_matching 以 v4 名义重跑，仍按验证选型 + 确认集一次性晋级
- [x] 对比 v3 / v4：真实文字未登录率、文本保留率、文本对打分影响、合成确认集指标
- [x] 补测试，更新文档

## 结果（2026-11-05）
- v4（`wide_stable`，MPS 训练）通过晋级检查，已写入 `server/models/matching.pt`；v3 备份在 `matching_v3.pt`
- 真实地陪文字：未登录字符 51.6% → 24.6%，文字保留 80.5% → 100%，文字对评分影响 0.038 → 0.077
- 合成确认集与 v3 持平（地陪 MAE 0.093 → 0.078，旅人 MAE 0.165 → 0.166，NDCG@5 差距 < 0.001）
- 参数 54,678 → 219,174；3072 对 CPU 推理 69 → 117 ms
- 全部 46 个测试通过
- 未解决：超过 256 字的简介尾部仍被截断；晋级检查只对比 v1，v3 对比为人工补测

---

# AI 帮我写：简介、亮点和套餐行程（后端）

权威说明：已合并的 `docs/AI_ITINERARY.md`（PR #2；与口头简报冲突时以文档为准）。本 PR 只做文档第 7 节的 1–3 步，不含前端。

计划：
- [x] `server/ai_draft.py`：本地规则引擎。简介复用 `polish_text`；亮点按关键词和服务类型凑满 3 条（每条 ≤ 20 字）；行程只抽取原文里的地点，不够用「沿途散步 / 自由拍照 / 休息 / 根据你的兴趣现场调整」补位；时间递增且不超过套餐时长，傍晚从 17:00 起
- [x] `server/polish_providers.py`：`draft()`、`draft_system_prompt()`（只许 JSON）、`parse_draft()`（类型、数量、长度、时间、顺序、时长、不接地的地点、多余字段都不通过，失败走现有回退）
- [x] `POST /api/ai/profile-draft`：登录检查持锁，生成不持锁；`part` 只接受文档里的 `all|bio|highlights|itinerary`（行程按一整块重写，不按单个套餐）
- [x] `POST /api/guides` 接收可选 `highlights` 和 `itineraries`，`make_packages` 写入 `key` 和 `itinerary`
- [x] 测试：本地引擎、校验器、接口、一条「生成 → 发布 → 详情」旅程
- [x] 跑完整 unittest，更新 README 的接口说明和测试数量

## 结果（2026-11-09）
- 已 rebase 到含 `docs/AI_ITINERARY.md` 的 main（PR #2）。`part` 只用文档里的四个值，没有做按单个套餐重写
- 本地引擎对示例原文抽出「人民公园」「玉林路」，不写鹤鸣茶社、宽窄巷子；模型输出对不上就回退，并带 `fallbackFrom`
- `python3 -m unittest discover -s tests -v`：81 项通过，12 项因未安装 PyTorch 跳过（原 65 + 新增 16）
- 本 PR 只有后端。发布页按钮和详情页时间线留给前端 PR

## 审核跟进（2026-11-09）
- [x] `POST /api/ai/profile-draft` 按用户限流（无用户 id 时按 IP），默认 60 秒 8 次，可用 `QINGHE_DRAFT_RATE_LIMIT` / `QINGHE_DRAFT_RATE_WINDOW` 调整；超出返回 429。本地引擎和外部模型共用额度
- [x] `variant` 不再把超大整数转成 float。不是 0–20 的整数时返回 400，而不是 500
- [x] 行程活动里的茶社、餐厅、里、园等也会做地点核对；本地行程最后一站比套餐结束早至少 30 分钟，并且落在 15 分钟刻度上
- [x] 单字结尾至少要有两个字的专名；回到酒店、傍晚到夜里、去朋友家里坐坐不会被当成地点

# AI 帮我写：发布页和详情页时间线（前端）

权威说明：`docs/AI_ITINERARY.md`。后端已在 main。本分支只做发布页、详情页，以及一刻钟中点的取整修正。不改 README。

计划：
- [x] 发布页「AI 帮我写」：两三句话生成简介、3 条亮点、三个套餐行程；每块可换一版；采用后能改
- [x] 加载、429 / 400 / 断网的中文提示；本地引擎有一行说明
- [x] 发布时三个套餐的行程都要带上，缺一个就拦住
- [x] 详情页按套餐展开时间线；没有 `itinerary` 的旧套餐不显示，也不按 `key` 去取
- [x] 生成文字用 textContent，不把模型输出拼进 innerHTML
- [x] `_quarter_hour` 的 7.5 分钟中点改为向上取整，并补测试
- [x] `python3 -m unittest discover -s tests -v`，再用本地引擎走一遍页面

## 结果（2026-11-09）
- 发布页主按钮「AI 帮我写」弹出与润色同风格的草稿；每块可「换一版」，「全部采用」写回简介、亮点和三个套餐，发布前仍可改
- 缺任一行程时不提交，并说明缺的是哪一个套餐。详情页只在套餐自己有 `itinerary` 时展开时间线；林小满这类旧页没有开关
- `_quarter_hour(7.5)` 现在是 15，不再先截成整数再加 7。三小时五站的示例时间改为 10:00 / 10:45 / 11:15 / 12:00 / 12:30
- `python3 -m unittest discover -s tests -v`：90 项通过，12 项因未安装 PyTorch 跳过。README 未改
