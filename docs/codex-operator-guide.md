# 设备方 Codex 操作指南

使用方式：完整解压 main.zip，用 Codex 打开解压目录根部，读取 START_HERE.md。下列命令由设备方 Codex 执行，操作员无需手工操作终端。

## 1. 首次准备与完整性检查

检查 Python 环境。共用检索/校验/打包只需 Python 3.10+ 和本规则包 requirements.txt；已在本次 macOS Python 3.12 环境验证，尚未在 Windows 现场运行。Windows 可用 `py -3 -m venv .venv` 建立环境，并用 `.venv\Scripts\python.exe` 替代以下 python；macOS 可用 `python3 -m venv .venv` 和 `.venv/bin/python`。

```sh
python -m pip install -r rules/releases/codex-trial-v001/requirements.txt
python scripts/operator_trial.py verify-rules
python scripts/operator_trial.py demo --job demo-001
python scripts/operator_trial.py package --job demo-001
```

demo 使用现有 v002 文件走通复制、校验、回放和打包，不读取 PDF，也没有生成新词。重复演示换一个未使用的 job-id。不能把 demo 反馈冒充订单试绣。

如果采用现有曲线生成器，按其说明补齐 numpy/scipy 等依赖，并记录实际依赖版本。发生权限或依赖问题时说明具体原因；不得因此静默跳过校验。

## 2. 导入本地订单

```sh
python scripts/operator_trial.py init --job order-001 --pdf "本机真实订单路径.pdf"
```

上面的 PDF 路径必须替换为用户给定真实路径。工具把原 PDF 复制到 `orders/local/order-001/input.pdf` 并记录 SHA256，不发送到 GitHub。创建 `orders/local/order-001/order.json` 和 `build/operator/order-001/plan.json`。

Codex 使用可用的 PDF 读取能力提取字段，必要时查看页面图像；扫描件可能需要 OCR。此处没有内置固定 OCR。阅读过程是否使用联网模型由所用 Codex 环境决定，不宣称离线识别。

填写 order.json：文字、字体、宽度、分行、对齐和来源页号；核对后设置 field_review。alignment 使用 single_line、left、center、right；text 与 lines 的文字须一致。装饰单独记录到 design.decorations，不混入文字。不能把模板中的 null 当默认订单。重要字段有真实歧义时向操作方确认。

## 3. 检索与选参考

```sh
python scripts/operator_trial.py search --text "Bulldogs" --font Font2
```

这是文件名候选检索，不是字形识别或精确订单匹配。核对候选实际图形和尺寸，再把路径、SHA256、用法写入 plan.json。例如：

```json
{"path":"examples/bulldogs-font2/source.DST","sha256":"以实际校验值替换","usage":"说明参考的文字、笔段、进出方向及针号范围"}
```

选择 route：exact_reuse、adapt_reference、compose 或 experimental。不能把大小写不同、带装饰、字体不明的样本自动当作完整匹配。

## 4. 生成本轮候选

Codex 按 RULES.md 实现或调用合适方法。新代码存 `build/operator/order-001/implementation/`，包含本单所需辅助模块；在 implementation_files 中填写项目相对路径。implementation_notes 记录执行命令及依赖版本，parameters 保存实际参数，hypotheses 保存未经验证假设。

输出统一命名 `build/operator/order-001/candidate.DST`。每个连续落针段都在 returns 中声明起收范围，按 DST 全部命令编号（从 1 开始，不含 END）。单连续 v002 示例：

```json
{"start_commands_1based":[1,10],"end_commands_1based":[821,829]}
```

这仅是指定 v002 文件的范围，不能复制用于新生成文件。新增跳转后需要逐段填写。不要通过随意挑选凑成 10 mm 的中间范围代替真实起收段。

## 5. 校验与展示

```sh
python scripts/operator_trial.py check --job order-001
```

工具会生成 validation.json、job.record.json、order.snapshot.json 和可离线打开的 replay.html；并在 orders/local/order-001/feedback/ 创建已绑定候选的中文反馈表。

退出码 0：共同软件检查通过；2：存在 needs_review 项；1：文件/环境/规则完整性等导致流程失败。0 不代表 Wilcom 或实机合格。校验记录保留每项结果，不能删掉失败项；不存在、模糊或未声明的部分保持待核对。

让操作方查看 `build/operator/order-001/replay.html` 及报告，核对字形、圆弧、回走、跳转、模式和潜在短针。软件不会自动识别单词或评判毛线效果。

## 6. 试绣与回传

操作方在 Wilcom 检查后安排试绣；每次重复复制独立反馈表。照片及修改后的实际 DST 放 orders/local/order-001/feedback/，记录改动，不替换 candidate.DST。首次 check 会保存 candidate.binding.json；同一 job 改变 DST 后将标为 needs_review，防止旧反馈混绑新针迹。原始候选需要改变时创建新的 job-id。

```sh
python scripts/operator_trial.py package --job order-001
```

工具重新检查当前候选，然后生成 `dist/order-001-feedback-001.zip` 和 SHA256；重复打包使用递增编号，不覆盖旧包。失败候选也可打包供分析，包内明确 needs_review。

包内包含本单字段、所选参考 DST、实际实现、规则基线、校验、回放和反馈。package-manifest.json 的 reference_path_map 将原参考路径对应到包内实际文件；job.record.json 记录实际校验环境和初次候选校验值。排除原始订单 PDF，未自动复制整个样本库。照片支持 jpg/jpeg/png，视频支持 mp4/webm，反馈支持 md/txt/json，修改后针迹支持 dst；其他格式先转换或另行明确处理。发送前检查包含哪些资料，工具不自动上传或发消息。

## 7. 版本更新与问题处理

保存本次下载原件及反馈包。规则升级使用新的解压目录，原订单和实验资料另存，避免用新版覆盖现场实现。ZIP 没有 .git 也能用规则 manifest 和 job.record 哈希追溯。

完整规则不能读取或检查失败时，先修复环境/缺失文件；规则缺口则记录实验假设和未通过项。新规则建议随反馈回传，由维护方审查后发布，不让每台电脑各自改共同阈值。

项目指令入口依据 OpenAI 的 [AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。这是项目指导机制，不是保证模型行为或生产结果的强制执行系统。

## 8. 首次现场回传要求

先在现场电脑完成 demo 自检，再选择一份真实订单。第一份订单优先选择能找到同词人工参考的内容，跑通 PDF 字段确认、生成记录、回放和反馈；随后再试未覆盖的新词。演示成功仅证明工具流程可运行。

若记录为 needs_review，先查看具体失败项，未解决时仍可导出诊断包回传；不能把这个状态当作已适合上机。对共同阈值有异议时附人工范例和理由，不在当前规则包内改掉检查。

每次回传填写 `feedback/trial-report.md`，没有试绣就注明“未试绣”及原因，不填写接受结论。复制多份反馈表分别记录重复试绣。新增实现和所有参数必须留在包内，便于维护方复现。
