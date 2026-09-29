# 开发与发布说明

当前代码是 Bulldogs 单案例原型。路径边界、局部规则仍有案例专用逻辑；整理目录不代表已经实现通用学习或订单 OCR。

## 环境

已验证 Python 3.13.13。锁定文件列出当前运行所需版本；属于版本锁，不是跨平台 wheel 哈希锁。本地环境不提交 Git。

Windows（安装 Python 3.13 后，在项目根目录）：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\build_pilot.py
.\.venv\Scripts\python.exe scripts\package_operator.py
```

macOS / Linux：

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/build_pilot.py
.venv/bin/python scripts/package_operator.py
```

也可用 `uv venv --python 3.13 .venv` 和 `uv pip install --python .venv/bin/python -r requirements.lock.txt`。本次直接执行验证在 macOS 完成，Windows 命令按标准 venv 布局提供，尚未在 Windows 实机运行。

## 构建和检查

`build_pilot.py` 依次生成 DST、离线回放、报告和 `build-info.json`。后者记录代码文件校验值、Python/包版本和输入/输出 DST 校验值。默认输出 `build/bulldogs-font2-330/`，可通过 `--output build/<candidate-id>` 指定候选目录。

`generate_dst.py` 校验单个输入样本的 SHA256，防止另一份 DST 被错误套用本案例的固定针序边界。默认 330 mm 为已验证基线；单独调用 `--width` 只表示实验能力，其他尺寸未通过实机验证。回放/报告工具也支持相同 `--output`，应始终读取同一候选目录。

全部生成工具拒绝向 `releases/` 或 build/ 之外输出。重新生成 build/ 会更新候选，因此需要比较的候选应使用不同目录。图形与报告属于辅助产物，最终尺寸和回线长度均从 DST 回读。

完整原始 PDF/字体不参与当前 DST 复现。`assets/private/fonts/Font2.OTF` 存在时报告额外渲染字体参考图；缺少时明确跳过，不影响 DST、回放、针迹预览及验证。

```sh
python -m unittest discover -s tests -v
python scripts/verify_release.py
```

测试覆盖：正负坐标编码、缺失 END、错误范围、超界位移、冻结样本/交付 DST 校验、清单完整性、禁止覆盖发布目录及模板关联。不要使用 `python -O` 运行生成器：当前几何检查包含 assert。

## v001 复现标准

当前发布 DST SHA256 为 `fd76864135643559e075c8cc5ea224a67472f2c21b7873889c3506576461e092`。基线复现应首先比较该文件字节；若跨平台或修改算法导致不同，必须检查解码后的针序、坐标和实际度量，不能把文件替换进 v001。

报告文字、构建环境记录和图像元数据可能随工具更新改变；这不授权修改已交付版本。使用 `manifest.json` 检查已交付文件原件。

## 新版本发布流程

1. 以新候选 ID 构建，记录唯一主要改动，检查几何和局部差异。
2. 完成回读与人工预览，保留明确的未验证状态。
3. 审查通过后，将候选复制为新版本目录，例如 `releases/bulldogs-font2-330/v002/`，更新版本说明和变更记录；v001 保持不变。
4. 为新目录建立 `manifest.json`，列出版本 ID、状态、指标和全部交付文件的 bytes / SHA256。当前打包脚本默认针对 v001，新版本需明确调整所选版本并检查。
5. 完整性检查可用 `python scripts/verify_release.py releases/bulldogs-font2-330/v002`。该检查器当前仅适用本 Bulldogs 文件名。
6. 生成操作方包，反馈存到 `feedback/reviewed/`。实机结果与适用条件记录在反馈记录中；若需改变发布状态，建立新的发布记录，不原地改掉旧清单。

不要把“文件验证通过”写成“实机合格”。稳定笔段编号、通用参数配置、局部覆盖、自动候选比较仍属于后续开发任务，详见 [迭代方案](iteration-plan.md)。

## 上传 Git

项目已经初始化本地 `main` 分支，但未创建提交或配置远程。首次提交前检查：

```sh
git status --short
git ls-files --others --exclude-standard
git check-ignore assets/private/orders/order.pdf
```

确认范围后由项目所有者提交、添加自己的远程地址并推送。不使用 `git add -f` 强制加入客户订单或本地依赖。交付 ZIP 放 `dist/`，作为附件分发；Git 中保留未压缩版本文件便于差异与校验。
