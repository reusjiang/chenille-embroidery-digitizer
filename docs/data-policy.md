# 资料、清理与 Git 范围

整理后的根目录名为 `chenille-embroidery-digitizer`。文档内容保持中文，便于设备操作方使用；目录和新文件名采用英文。

## 保留并提交

- 开发脚本、测试、依赖版本及文档。
- 一个最小人工参考样本 `examples/bulldogs-font2/source.DST`，保留原始字节和来源校验。
- `releases/bulldogs-font2-330/v001/` 的 DST、回放、图像、逐针 CSV 和校验清单。
- 空白反馈模板；以后经审查的试绣记录。
- library/ 索引与标注、rules/ 规则、experiments/ 脱敏实验记录及 orders/templates/；索引含原始文件名，共享范围应与样本资料一致。
- v002 冻结候选及其最小复现输入。

## 原始资料位置与当前跟踪状态

| 原位置 | 当前位置 |
|---|---|
| 参考用的Dst文件/ | assets/private/dst-library/ |
| 参考用的EMB文件/ | assets/private/emb-library/ |
| 字体/ | assets/private/fonts/ |
| 绣花机图片/ | assets/private/machine-photos/ |
| 订单.pdf | assets/private/orders/order.pdf |

原始资料未删除。2026-10-13 核对发现以下目录已有文件被 Git 跟踪；目录名称 private 不具有自动排除作用。此次调整不取消跟踪，也不更改共享设置。

完整库包含大量不同订单/样本，原始 PDF 含客户姓名、地址和联系信息；这些不是操作方试绣本案例所必需的内容。原始字体与样本没有因目录整理而获得额外分发许可。默认仓库不附带开源许可证，不宣称第三方字体可自由再分发。

原订单与匿名案例的对应关系保存在本地 `assets/private/order-map.json`，其余订单的初步梳理保存在 `assets/private/order-review.md`。后续需要向指定合作方共享完整原始资料时，按明确的资料范围单独处理，避免将整个私有目录直接纳入 Git。

## 已清理/移出交付范围

- 临时 PDF 页面渲染、联系表、分析脚本和缓存（原 tmp/）。
- 本地 .venv 环境、__pycache__、.DS_Store、IDE 工作区和空的本地 MCP 配置。
- 旧 output/ 下的重复 ZIP；新的操作方 ZIP 从冻结版本与指南生成到 dist/。
- 用不到的 PDF/OCR/图像骨架处理依赖。当前运行依赖保留在 requirements.lock.txt。

历史 readme 要求保留为 `docs/digitizing-spec.md`；任务目标保留为 `docs/project-goals.md`；迭代方案移到 `docs/iteration-plan.md`。

## 反馈资料

设备方的原始反馈先进入本地 `feedback/inbox/`。整理掉不相关个人信息、确认关联版本后，将适合共享的记录放到 `feedback/reviewed/<trial-id>/`。保留失败记录，不能用空白模板替代真实试绣证据。大视频不默认进入 Git，可在记录中注明双方约定的受控存放位置。

## 新增订单工作区

`orders/local/` 保存实际订单与生成记录；除 README 外新增文件默认不进入 Git。原始订单 PDF 保持原路径。Git 忽略仅影响未跟踪文件，不能从已有提交中移除资料。
