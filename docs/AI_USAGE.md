# AI collaboration and resource provenance

The course explicitly permits collaboration with generative AI, including specification, testing, CI/CD, documentation and code review. This does not remove the requirement for original group work and attribution of external resources.

## Assistance actually used in this chat

The user supplied an existing Qinghe Node.js/browser prototype. OpenAI Codex helped inspect it, migrate the HTTP API to Python, preserve its data/password format, create integration tests, and update startup instructions. After the course requirements were supplied, Codex read the PDF and helped add the required `main.py` CLI, shared pricing, requirements mapping, specification, test/review records, a CI configuration, packaging support and presentation/report guidance.

These are AI-assisted changes, not claims that any named student independently authored them. The group must verify the original prototype's provenance and identify the actual work each member performs. Do not describe this inherited prototype as created from scratch by the group unless that is true and supported.

## Useful prompt / review trail to retain

Actual user requests included reading the project, converting it to Python, and aligning it to the supplied course requirements. Keep the relevant chat or a truthful summary as development evidence. Record future prompts, generated outputs, human changes, bugs found and checks performed. Do not invent conversations or human reviews.

## External resources

- Python standard library: `https://docs.python.org/3/` (HTTP, file IO, JSON, crypto, threading, CLI, testing and ZIP).
- GitHub Actions: checkout and setup-python actions are used only in CI; no CI run is claimed merely from adding the file.
- Photographs: see `CREDITS.md` for Unsplash / Wikimedia sources and licence obligations. Verify attribution and permissions before submission.
- OpenAI Codex: used as a development collaborator, not as a runtime dependency or a remote model behind the local polish feature.

## Before submission

Each member should understand their claimed contribution, independently check the relevant functions and tests, record modifications, cite external material in the report, and comply with any additional Moodle/instructor AI disclosure rules. The actual group membership and individual work are not populated here.

## 双边神经匹配扩展

用户进一步要求简单 Transformer 与异构图。Codex 协助实现 PyTorch 文本编码、按关系区分的图传播、独立双向评分头、合成样例训练、双端页面和测试。PyTorch 与 NumPy 为外部依赖，PyG 文档只作概念参考，没有安装 PyG。参见 `MATCHING.md` 的模型边界与官方资料引用；不把合成偏好冒充真实用户反馈。

## 优化实验

Codex 进一步协助统一训练/验证指标、按人物和主题句模板划分、从潜在偏好生成标签、早停、梯度裁剪、结构化相容性特征、候选域训练、三种子集成及 NDCG 评价。第一轮未通过晋级的试验也保留；第二轮只按验证结果选择，再用新的合成确认集验收。所有结果仍属于规则蒸馏，未采集或编造真实反馈。详见 OPTIMIZATION.md。
