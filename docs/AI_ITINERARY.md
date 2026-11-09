# 方向 3：AI 一键生成地陪简介和推荐行程

> 作者：Kate（创意总监）· 2026-11-09 · 状态：方案，待 Eve 实现、Tina 审核

## 1. 为什么做

INT6181 的主题是 AI。现在的 AI 润色（`server/ai_polish.py`、`server/polish_providers.py`、`public/js/components/ai-polish.js`）只是把已有文字改得更通顺。演示时最打动人的是：**本地人只写两三句话，AI 就帮他生成一份完整的地陪主页**，包括简介、亮点和每个套餐的推荐行程。旅人看到的是具体的路线，而不是空泛的"带你玩"。

一句话目标：**两句话进，一份能直接发布的地陪主页出。**

## 2. 用户体验

### 2.1 本地人发布页（`public/js/pages/become.js`）

1. 在"个人介绍"输入框旁边，除了现有的「AI 润色」，新增主按钮 **「AI 帮我写」**。
2. 用户只需写几句话，例如："我在成都长大，喜欢泡茶馆、吃苍蝇馆子，周末常去人民公园和玉林路。"，再选好城市和服务类型。
3. 点击后弹出与现有润色弹窗同风格的生成弹窗（复用 `.ai-polish-modal` 样式），分三块预览：
   - **简介**：200 到 400 字，第一人称；
   - **三个亮点**：替换现在写死的 `highlights`（`城市本地人私藏路线` 等）；
   - **推荐行程**：对应三个套餐（半日轻游 4 小时、全天深度游 8 小时、傍晚轻陪游 3 小时），每个套餐 3 到 5 个时间节点。
4. 每一块都可以单独「换一版」，也可以整体「全部采用」。采用后内容填回表单，用户还能手动改。
5. 弹窗底部保留一句承诺：「只用你写到的地点和经历，不会替你编造」。

### 2.2 旅人详情页（`public/js/pages/detail.js`）

在每个套餐卡片下加一个可展开的 **「行程安排」时间线**，例如：

```
14:00  人民公园鹤鸣茶社 · 盖碗茶、看本地人打牌
15:30  步行到宽窄巷子附近的小巷 · 拍照
17:00  玉林路 · 找一家苍蝇馆子吃晚饭
```

没有行程的旧地陪不显示这块，界面不变。

## 3. 后端设计

### 3.1 新接口 `POST /api/ai/profile-draft`

请求：

```json
{
  "notes": "我在成都长大，喜欢泡茶馆……",
  "city": "成都",
  "services": ["美食探店", "城市漫步"],
  "packages": [
    {"key": "half", "name": "半日轻游", "duration": "4 小时"},
    {"key": "full", "name": "全天深度游", "duration": "8 小时"},
    {"key": "evening", "name": "傍晚轻陪游", "duration": "3 小时"}
  ],
  "part": "all",
  "variant": 0
}
```

- `notes`：6 到 300 字；`part`：`all` | `bio` | `highlights` | `itinerary`，用于单块「换一版」。
- 需要登录，与 `polish_route` 一样只在登录检查时持锁，模型调用不持锁。

响应：

```json
{
  "bio": "……",
  "highlights": ["……", "……", "……"],
  "itineraries": {
    "half": [{"time": "14:00", "place": "人民公园鹤鸣茶社", "activity": "盖碗茶、看本地人打牌"}]
  },
  "provider": "openai",
  "model": "…",
  "fallbackFrom": ""
}
```

### 3.2 复用 provider 架构

`polish_providers.py` 已经有可插拔的 provider、超时、回退和输出清洗，直接扩展，不另起一套：

- 给 `PolishProvider` 增加 `draft(request)` 方法；`OpenAICompatibleProvider` 和 `AnthropicProvider` 用新的 `draft_system_prompt()`，要求模型**只输出 JSON**。
- 新增 `parse_draft(raw)`：去掉 `<think>`、Markdown 代码块，`json.loads`，再逐字段校验类型和长度（bio ≤ 600 字、亮点每条 ≤ 20 字且正好 3 条、每个行程 3 到 5 个节点、`time` 符合 `HH:MM`）。任何一项不合格都抛 `ProviderResponseError`，走现有回退逻辑。
- 配置沿用 `QINGHE_POLISH_*` 环境变量，不新增密钥字段。

### 3.3 提示词要点（`draft_system_prompt`）

1. 只能使用 `notes` 里出现的地点、经历和爱好；可以安排顺序、时间和衔接，但**不新增具体店名或景点**。
2. 素材不够填满行程时，用"沿途散步""自由拍照""根据你的兴趣现场调整"这类不具体的节点补位，而不是编地名。
3. 行程总时长不超过套餐时长；傍晚套餐从 17:00 以后开始。
4. 第一人称、温暖、不夸张；不写价格、资质和安全承诺。
5. `variant > 0` 时换一种写法。

### 3.4 本地引擎回退（没有模型也能演示）

新增 `server/ai_draft.py`，规则生成，保证断网演示也不翻车：

- **简介**：先调用现有 `polish_text(notes, 'guide', city, variant)`。
- **亮点**：从 notes 里按关键词表（茶、咖啡、美食、夜景、拍照、博物馆、徒步、小巷等）匹配，拼成"带你去泡老茶馆"这类短句；不足 3 条时用服务类型补齐。
- **行程**：用简单规则从 notes 中提取地点（`去/在/逛/到` 后面、以 `公园|路|街|巷|寺|馆|山|湖|市场` 结尾的词），按套餐时段平均分配时间；提取不到时用通用节点补位。
- 结果标记 `provider: "local"`，前端显示"本地 AI 引擎"。

## 4. 数据存储

- `POST /api/guides` 新增可选字段：
  - `highlights`：3 条字符串，每条 ≤ 20 字；不传时保持现在的默认值。
  - `itineraries`：`{ half|full|evening: [{time, place, activity}] }`，校验同 3.2。
- `make_packages()` 增加可选参数，把对应行程写入每个 package 的 `itinerary` 字段。
- 旧数据没有 `itinerary` 字段，前端判空即可，不需要迁移。

## 5. 测试（加到 `tests/`）

1. `test_polish_providers.py`：`parse_draft` 对合法 JSON、包在代码块里的 JSON、缺字段、超长、时间格式错误的处理。
2. 新增 `test_ai_draft.py`：本地引擎对示例 notes 能提取出"人民公园""玉林路"，且每个行程 3 到 5 个节点、时间递增、不超出套餐时长。
3. `test_server.py`：未登录 401；notes 过短或过长 400；provider 失败时回退到本地且返回 `fallbackFrom`。
4. `test_user_journeys.py`：一个完整流程，写两句话，生成，采用，发布，详情页 API 返回 `packages[].itinerary`。

## 6. 验收标准

- [ ] 不配置任何模型时，「AI 帮我写」在 3 秒内返回完整草稿（本地引擎）。
- [ ] 配置 OpenAI 兼容模型时，返回的行程地点全部来自用户写的内容。
- [ ] 每一块都能单独「换一版」，「全部采用」后表单内容正确。
- [ ] 详情页套餐能展开行程时间线；旧地陪页面没有变化。
- [ ] 所有新旧测试通过，GitHub Actions `tests.yml` 全绿。

## 7. 建议的实现顺序（给 Eve）

1. 后端：`ai_draft.py` 本地引擎和测试（先保证离线能演示）。
2. 后端：`/api/ai/profile-draft` 接口和 `parse_draft`，接上 provider。
3. 后端：`POST /api/guides` 接收 `highlights` 和 `itineraries`。
4. 前端：发布页「AI 帮我写」弹窗。
5. 前端：详情页行程时间线。
6. 更新 `docs/AI_USAGE.md` 和 `preview/` 截图，方便课程展示。

建议拆成两个 PR：第 1 到 3 步一个（后端），第 4 到 6 步一个（前端），Tina 审起来更轻松。
