# 青禾 · 城市轻兼职

[![Python tests](https://github.com/Woodensnow/Qinghe/actions/workflows/tests.yml/badge.svg)](https://github.com/Woodensnow/Qinghe/actions/workflows/tests.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-2f6f57)
![EdUHK INT6181](https://img.shields.io/badge/EdUHK-INT6181-2F6F57)

> 找位本地人，陪你慢慢逛。也把你的闲暇时间，变成一段新的旅程。

青禾是香港教育大学 INT6181 的课程项目，一个双端网站：**旅人**可以找懂城市的本地地陪，**熟悉城市的人**可以发布自己的地陪服务，把空闲时间变成一份副业。

- 覆盖 **34 个省级行政区、151 座城市**，当前重点打磨「地陪」板块；摄影、模特、博物馆讲解员、NPC 以「即将开放」入口预留。
- **双边匹配**：字符级 Transformer + 异构图神经网络，同时给出「旅人想不想选他」和「地陪想不想接这单」两个方向的分数。
- **AI 帮我写**：地陪只写几句熟悉的地方，就能得到简介、三条亮点和三份套餐行程；地点只取自用户写的内容，不替人编造。
- **AI 润色**：把已写好的简介改顺。两项 AI 功能默认用本地引擎即可使用，也可通过环境变量接入 OpenAI 兼容接口、Ollama 或 Claude。
- 后端只用 Python 标准库，前端是原生 HTML / CSS / JavaScript，无需构建步骤。

![青禾首页](./preview/home-hero.jpg)

| 地陪详情 | 私聊消息 |
| --- | --- |
| ![地陪详情页](./preview/guide-detail.jpg) | ![私聊消息中心](./preview/messages.jpg) |
| **个人资料与照片墙** | **AI 文本润色** |
| ![个人资料](./preview/profile.jpg) | ![AI 润色](./preview/ai-polish.jpg) |

---

## 目录

- [快速开始](#快速开始)
- [功能](#功能)
- [双边匹配：Transformer + 异构图](#双边匹配transformer--异构图)
- [AI 功能：帮我写与润色](#ai-功能帮我写与润色)
- [测试](#测试)
- [项目结构](#项目结构)
- [API](#api)
- [数据与安全](#数据与安全)
- [课程提交](#课程提交)
- [图片版权](#图片版权)

---

## 快速开始

需要 **Python 3.10+**。网站本身只用标准库；双边匹配推荐另需 PyTorch 和 NumPy（不装也能运行网站，只是匹配页提示缺少依赖）。

### macOS / Linux

```bash
git clone https://github.com/Woodensnow/Qinghe.git
cd Qinghe
python3 -m venv .venv
.venv/bin/pip install -r requirements-matching.txt   # 可选：启用双边匹配
./start.sh
```

### Windows

```powershell
git clone https://github.com/Woodensnow/Qinghe.git
cd Qinghe
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-matching.txt   # 可选：启用双边匹配
.\start.ps1
```

也可以直接双击 `start.bat`。

启动后打开 **<http://127.0.0.1:4173>**，在终端按 **Ctrl+C** 停止（macOS / Linux 也可运行 `./stop.sh`）。

- 启动脚本优先使用项目里的 `.venv`，也可以用环境变量 `PYTHON_BIN` 指定解释器。
- 默认监听 `127.0.0.1:4173`，用 `HOST`、`PORT` 修改。不要同时运行多个实例操作同一份数据。
- 首次启动会根据 `server/seed-data.json` 自动生成业务数据 `server/data.json`。

### 演示账号

| 邮箱 | 密码 |
| --- | --- |
| `demo@qinghe.cn` | `qinghe123` |

也可以点登录弹窗里的 **一键体验**。演示账号预置了已确认和已完成的预约各一条、一项暂停中的地陪服务、带封面和照片墙的个人资料，以及两段私聊。

### 双边匹配测试账号

预置地陪没有填写匹配偏好，只靠演示账号看不到推荐结果。服务启动后运行：

```bash
.venv/bin/python tools/seed_matching_demo.py        # Windows：.\.venv\Scripts\python.exe tools\seed_matching_demo.py
```

脚本通过网站自己的接口创建 4 个上海地陪（`guide1`–`guide4@qinghe.test`）和 4 个旅人（`traveler1`–`traveler4@qinghe.test`），兴趣两两对应，并打印双方的推荐排序。测试密码见脚本里的 `TEST_PASSWORD`；可重复运行，不会重复创建。

> 在同一台电脑上同时登录两个账号：用 `http://localhost:4173` 和 `http://127.0.0.1:4173` 分别打开即可，登录状态互不影响。

### 重置演示数据

先停止服务，再运行（会清空所有用户、预约、私聊和上传图片，恢复初始演示数据）：

```bash
python3 main.py --reset          # Windows：.\start.ps1 --reset
```

若进程意外退出留下 `server/server.pid`，确认服务已关闭后删除该文件再重置。

---

## 功能

**账号**
- 邮箱注册 / 登录 / 退出，密码用 `scrypt` 加盐哈希；Bearer Token 会话有效期 7 天
- 未登录时预约会弹出登录框，登录后继续完成预约

**地陪**
- 151 座城市按省份分组；首页按城市、日期、服务类型搜索
- 列表支持热门城市、服务、语言、价格、关键词筛选与多种排序
- 详情页：照片画廊、介绍、亮点、套餐、评价、服务保障
- 预约：选套餐、日期、时间、人数，超过 4 人自动加收服务费；可查看、取消、再次预约
- 成为地陪：发布表单带实时预览，封面可选预置图或本地导入；可暂停 / 恢复接单
- 套餐可附带「行程安排」时间线，旅人在详情页展开查看

**双边匹配**
- 旅人填写行程（城市、日期、时长、人数、预算、服务、语言、兴趣、节奏、描述）
- 地陪填写接单偏好（接待人数、接单星期、休息日、兴趣、节奏、描述）
- 先按城市、语言、服务、预算、档期和人数做硬筛选，再由模型给出双方视角的分数与推荐理由
- 地陪可直接在推荐卡片上联系旅人

**私聊**
- 从地陪卡片、详情页或匹配结果发起私聊；`/messages` 消息中心，双方均可回复
- 未读计数，4 秒轮询收新消息；移动端列表 / 聊天切换

**个人资料**
- 本地上传头像（自动方形裁切）、主页封面、最多 6 张照片墙；图片在浏览器端压缩
- 个人简介和地陪介绍支持 **AI 润色**，先预览再替换，可再润色一次

**AI 帮我写**
- 发布服务时写下 6–300 字的本地经历，一键生成第一人称简介、三条亮点，以及半日轻游（4 小时）、全天深度游（8 小时）、傍晚轻陪游（3 小时）三份行程
- 每一块都能单独「换一版」，也可以「全部采用」后再手动修改
- 行程地点只来自用户写到的内容，时间对齐到一刻钟

**体验**
- 淡绿 + 白色视觉，响应式适配桌面、平板、手机
- 灯箱、Toast、确认弹窗、骨架屏、空状态；支持 `prefers-reduced-motion`
- 基础无障碍：跳转链接、焦点样式、弹窗焦点循环、Esc 关闭

---

## 双边匹配：Transformer + 异构图

1. **硬条件筛选**：城市、共同语言、所需服务、对应时长套餐、预算、地陪档期与接待人数不满足的候选直接排除，并统计排除原因。
2. **文本编码**：旅人和地陪的资料拼成一段文字，按字符编码，经 1 层 Transformer Encoder（4 头注意力）后做均值池化。
3. **异构图传播**：旅人、地陪与城市、服务、语言、兴趣、节奏等属性节点相连，每种关系使用独立参数传播信息。
4. **双向评分**：两个独立评分头分别给出旅人方向和地陪方向的分数，三个随机种子的模型取平均，再用调和平均得到综合分——任何一方不情愿都会拉低总分。

当前部署的是 **v4 三成员集成**（`server/models/matching.pt`，共 219,174 个参数）。相比 v3，v4 用更贴近真实写法的合成文字训练，并在训练时随机遮盖 15% 的字符：真实地陪资料的未登录字符比例从 51.6% 降到 24.6%，文字长度上限从 128 提高到 256 个字符。

![v4 训练损失与确认集对比](./docs/matching_optimization.png)

**重新训练**（Apple 芯片可用 MPS，其他机器自动用 CPU）：

```bash
.venv/bin/python tools/train_matching.py --preset wide_stable --device auto   # 训练单个候选模型，输出到 output/，不覆盖线上权重
.venv/bin/python tools/refine_matching.py --device auto                       # 3 种配置 × 3 个种子，按验证集选型，确认集验收后才替换线上权重
.venv/bin/python tools/plot_matching_optimization.py                          # 重新生成损失与对比图（需 matplotlib，并先运行上一步）
```

> 模型只在**合成偏好数据**上训练，推荐分是排序参考，不是接受或成交概率；真实推荐效果仍需真实数据验证。

详细说明：[匹配算法完整说明](docs/匹配算法完整说明.md) · [优化实验报告](docs/OPTIMIZATION.md) · [Encoder 深度对照](docs/ENCODER_DEPTH.md)

---

## AI 功能：帮我写与润色

「AI 帮我写」（`POST /api/ai/profile-draft`）和「AI 润色」（`POST /api/ai/polish`）共用同一套模型提供方。默认使用内置本地引擎（`local`），**什么都不配置也能用**。想要更好的效果时，用环境变量切换到外部模型，不用改代码：

| 环境变量 | 说明 | 默认值 |
| --- | --- | --- |
| `QINGHE_POLISH_PROVIDER` | `local` / `openai`（任何 OpenAI 兼容接口）/ `anthropic`（Claude） | `local` |
| `QINGHE_POLISH_MODEL` | 模型名，外部提供方必填 | — |
| `QINGHE_POLISH_BASE_URL` | 接口根地址（不含 `/chat/completions`） | 各提供方官方地址 |
| `QINGHE_POLISH_API_KEY` | API 密钥，**只能**放在环境变量里 | — |
| `QINGHE_POLISH_API_KEY_ENV` | 沿用已有变量时填它的名字，例如 `ANTHROPIC_API_KEY` | `QINGHE_POLISH_API_KEY` |
| `QINGHE_POLISH_TIMEOUT` | 单次请求超时（秒） | `20` |
| `QINGHE_POLISH_FALLBACK` | 外部模型失败时：`local` 自动改用本地引擎；`off` 直接报错 | `local` |
| `QINGHE_POLISH_OPTIONS` | 合并进请求体的 JSON，例如 `{"temperature": 0.7}` | `{}` |
| `QINGHE_POLISH_CONFIG` | 配置文件路径 | `server/ai_polish.local.json` |

```bash
# 本地 Ollama（无需密钥）
export QINGHE_POLISH_PROVIDER=openai QINGHE_POLISH_BASE_URL=http://localhost:11434/v1 QINGHE_POLISH_MODEL=qwen2.5:7b

# Claude
export QINGHE_POLISH_PROVIDER=anthropic QINGHE_POLISH_MODEL=claude-haiku-5-5 QINGHE_POLISH_API_KEY_ENV=ANTHROPIC_API_KEY

# OpenAI 或其他兼容服务（DeepSeek、vLLM 等只需换 BASE_URL 和模型名）
export QINGHE_POLISH_PROVIDER=openai QINGHE_POLISH_MODEL=你的模型名 QINGHE_POLISH_API_KEY=你的密钥
```

非密钥设置也可以写进 `server/ai_polish.local.json`（已被 git 和打包脚本忽略，环境变量优先；文件里出现 `api_key`、`token` 等字段会被拒绝）：

```json
{"provider": "openai", "base_url": "http://localhost:11434/v1", "model": "qwen2.5:7b", "timeout": 30}
```

- 接口 `POST /api/ai/polish` 的请求格式不变，响应额外带 `provider`、`model`；回退到本地引擎时带 `fallbackFrom`。
- `FALLBACK=off` 时：配置错误返回 503，超时 504，其他失败 502。
- 模型输出会去掉代码块、引号、`<think>` 等包装，并按场景裁剪字数（个人简介 160 / 地陪介绍 600）。
- 调用模型时不占用全局数据锁，慢模型不会卡住网站其他请求。
- 「帮我写」按用户限流，默认每 60 秒 8 次，可用 `QINGHE_DRAFT_RATE_LIMIT`、`QINGHE_DRAFT_RATE_WINDOW` 调整。设计说明见 [AI 帮我写方案](docs/AI_ITINERARY.md)。

**新增提供方**：在 [`server/polish_providers.py`](server/polish_providers.py) 里写一个类并注册即可（润色实现 `polish`，帮我写实现 `draft`），超时、清理、裁剪和错误处理由统一入口负责。

```python
@register('my-model')
class MyProvider(PolishProvider):
    default_base_url = 'https://example.com/v1'
    needs_key = True

    def polish(self, request):          # request.text / scene / city / variant / limit
        result = self.post_json('/generate', {'model': self.model, 'prompt': system_prompt(request) + request.text},
                                {'Authorization': 'Bearer ' + self.settings.api_key})
        return result['output']
```

---

## 测试

```bash
.venv/bin/python -m unittest discover -s tests                              # 全部 91 项
.venv/bin/python -m unittest discover -s tests -p test_user_journeys.py -v  # 只跑 15 个用户故事
```

| 文件 | 内容 | 数量 |
| --- | --- | ---: |
| `test_polish_providers.py` | 模型提供方的配置、超时、回退、输出清理（用本地模拟服务，不访问外网） | 26 |
| `test_user_journeys.py` | 真实接口下的用户故事：筛选预约、雨天改订、地陪休假、多旅人私聊、照片墙、润色与帮我写等 | 15 |
| `test_server.py` | 登录、计价、发布、私聊、上传、并发写入，以及帮我写接口的校验、回退与限流 | 14 |
| `test_matching.py` | 模型可训练性、文本与图结构的贡献、双方视角流程 | 11 |
| `test_matching_evaluation.py` | 数据划分隔离、排序指标、最佳权重选择、文本截断与未知字符增强 | 9 |
| `test_ai_draft.py` | 帮我写引擎：地点提取、亮点、换一版与行程时间 | 8 |
| `test_cli.py` / `test_package.py` | 命令行菜单与课程打包 | 5 |
| `test_itinerary_client.py` | 前端行程校验（需要 Node） | 3 |

测试使用独立临时数据，不改动现有业务数据。模型相关测试在未安装 PyTorch 时自动跳过；`test_itinerary_client.py` 需要 PATH 里有 Node（CI 使用 Node 22）。每次推送由 [GitHub Actions](https://github.com/Woodensnow/Qinghe/actions) 在 Ubuntu / Windows、Python 3.10 / 3.12 上运行，另有一个任务安装 PyTorch 跑匹配测试。场景说明见 [测试文档](docs/TESTING.md)。

---

## 项目结构

```text
Qinghe/
├── main.py                    # 课程入口：命令行菜单 / --serve / --reset
├── start.sh · stop.sh         # macOS / Linux 启动与停止
├── start.ps1 · start.bat      # Windows 启动
├── requirements-matching.txt  # 双边匹配可选依赖（PyTorch、NumPy）
├── server/
│   ├── server.py              # HTTP 服务、路由与静态文件
│   ├── store.py               # JSON 文件存储与演示数据初始化
│   ├── seed-data.json         # 初始演示素材
│   ├── catalog.json           # 城市、服务、语言等枚举
│   ├── pricing.py             # 命令行与预约共用的计价规则
│   ├── auth_utils.py          # scrypt 哈希与会话 Token
│   ├── ai_polish.py           # 本地润色引擎
│   ├── ai_draft.py            # 本地「帮我写」引擎：简介、亮点与行程
│   ├── polish_providers.py    # 润色与帮我写共用的模型提供方接口
│   ├── matching_model.py      # Transformer + 异构图网络与双向评分头
│   ├── matching_service.py    # 硬条件、档期与推荐排序
│   ├── matching_api.py        # 行程、偏好、推荐与联系接口
│   ├── matching_data.py       # 合成训练数据与教师标签
│   └── models/                # 模型权重（matching.pt 为线上 v4，另存 v1 / v3）
├── public/
│   ├── index.html · css/styles.css
│   ├── js/                    # 路由、API 封装、页面与组件（ES Modules）
│   ├── assets/images/         # 演示图片
│   └── uploads/               # 用户上传的图片
├── tools/                     # 训练、选型、绘图、测试账号、打包脚本
├── tests/                     # 单元与接口测试
├── docs/                      # 算法说明、实验报告、规格与课程文档
├── 训练图表/                   # 模型架构图与训练曲线
└── preview/                   # README 截图
```

---

## API

需登录的接口在请求头带 `Authorization: Bearer <token>`。

**账号与资料**

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register` | 注册并自动登录 |
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 退出登录 |
| GET | `/api/auth/me` | 当前用户 |
| PATCH | `/api/profile` | 更新昵称、城市、简介 |
| POST / DELETE | `/api/profile/photo` | 上传 / 移除头像、封面、照片 |
| POST | `/api/ai/polish` | AI 润色个人简介或地陪介绍 |
| POST | `/api/ai/profile-draft` | AI 帮我写：生成简介、亮点和套餐行程（限流） |

**地陪与预约**

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET | `/api/meta` | 城市、服务、语言、封面等元信息 |
| GET | `/api/guides` | 地陪列表，支持筛选与排序 |
| GET | `/api/guides/:id` | 地陪详情 |
| GET | `/api/guides/mine` | 我发布的服务 |
| POST | `/api/guides` | 发布地陪服务 |
| PATCH | `/api/guides/:id` | 暂停 / 恢复接单（仅发布者） |
| POST | `/api/uploads` | 上传封面等图片 |
| POST | `/api/bookings` | 创建预约 |
| GET | `/api/bookings/mine` | 我的预约 |
| PATCH | `/api/bookings/:id/cancel` | 取消预约 |

```text
/api/guides?city=上海&service=城市漫步&language=英语&minPrice=200&maxPrice=400&sort=rating&q=咖啡
```

**双边匹配**

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/matching/meta` | 可选兴趣、节奏，以及模型和 PyTorch 是否可用 |
| GET / POST / DELETE | `/api/matching/trip` | 查看 / 保存 / 停止展示我的行程 |
| PATCH | `/api/matching/preferences/:guideId` | 保存地陪接单偏好 |
| GET | `/api/matching/guides` | 旅人视角：为我的行程推荐地陪 |
| GET | `/api/matching/travelers?guideId=` | 地陪视角：为我的服务推荐旅人 |
| POST | `/api/matching/contact` | 地陪联系推荐的旅人 |

**私聊**

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET / POST | `/api/conversations` | 会话列表 / 发起或获取会话 |
| GET / POST | `/api/conversations/:id/messages` | 读取消息并标记已读 / 发送消息 |
| GET | `/api/messages/unread` | 未读总数 |

---

## 数据与安全

- 这是可交互的**演示项目**，不是生产级交易系统。
- 数据保存在 `server/data.json`（已被 git 忽略），上传图片保存在 `public/uploads/`，重启后仍在。
- 密码用 `scrypt` 加盐哈希，接口不返回哈希和盐；上传只接受 JPG / PNG / WebP，校验文件头并限制 5MB。
- AI 润色的 API 密钥只从环境变量读取，不写入代码、配置文件或仓库。
- 私聊用 HTTP 轮询模拟实时消息；未接入短信 / 邮件验证、支付、地图、实名认证和对象存储。
- 正式上线前至少需要：数据库、对象存储、HTTPS、频控与风控、实名认证、支付与退款、隐私合规和内容审核。
- 平台定位为正规的城市旅行陪伴服务，社区公约要求公开场所见面、平台内沟通，拒绝私下交易和越界邀约。

---

## 课程提交

INT6181 要求的 Python 入口是 `main.py`：

```bash
python3 main.py
```

进入命令行菜单，可查询地陪、选择套餐计算 1–8 人报价、启动网页服务和运行测试；账号、预约和私聊在浏览器中完成。课程要求对照、规格、代码评审和展示提纲见 [课程对照清单](docs/COURSE_REQUIREMENTS.md)。

打包提交（把 3 换成实际组号）：

```bash
python3 tools/package_project.py --group 3
```

生成 `output/group3_project.zip`，包含源码、初始演示数据、模型权重、测试和文档，不包含现有账号、聊天、预约、上传图片和本地润色配置。提交前请在独立目录解压，运行 `python main.py` 和测试确认。

---

## 图片版权

演示图片来自 Unsplash 与 Wikimedia Commons，作者、来源和许可见 [CREDITS.md](./CREDITS.md)。用于正式产品时请替换为自有版权图片。
