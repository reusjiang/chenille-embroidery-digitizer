# Chenille Embroidery Digitizer

雪尼尔刺绣打带与实机反馈迭代项目。当前保留 **Bulldogs / Font2 / 330 mm** 基线案例，并提供 **CHENILLE-REF-v002** 三款试绣候选，基于人工同词 DST 的笔顺重建路径。尚未实现任意订单 PDF 自动打带，也尚未完成 Wilcom / 大豪设备试绣验收。

## 设备方 Codex 规则试用包

**下载 main.zip 后，用自己的 Codex 打开解压根目录，从 [START_HERE.md](START_HERE.md) 开始。** 本版为 `codex-trial-v001`：提供规则、样本检索、任务建立、统一校验、离线回放和反馈打包。PDF 阅读和本单生成逻辑由设备方 Codex 执行或实现，尚无固定通用自动生成引擎。

[操作指南](docs/codex-operator-guide.md) · [确定规则](rules/releases/codex-trial-v001/RULES.md)。使用新订单时走这条入口；仅试绣现有三款时使用下面的 v002。

## 最新候选：CHENILLE-REF-v002（2026-10-13）

依据 50 份数字针路对照，新增 **Bulldogs / Font2、Bulldogs / Font3、Cougars / Font3** 三款可试绣候选，包含 DST、逐针回放、三方对照、校验报告和独立反馈表。已通过文件检查，**尚待 Wilcom 检查与实机试绣**；另外 47 款未重新生成。

- [v002 方案说明](releases/reference-guided/v002/README.md) · [候选网页总览](releases/reference-guided/v002/index.html)（本地用浏览器打开）。
- [生成配置](configs/feedback-v002.json) · [冻结输入与来源](examples/feedback-v002/README.md)。
- 本地操作方交付包：`dist/CHENILLE-REF-v002-operator-kit.zip`，完整解压后打开 `index.html`；ZIP 默认不纳入 Git。

本版使用同词人工参考重建路径，尚未修复缺失的通用字体中线生成器。原 BULL-F2-330-v001 继续保留为独立基线。

## 仅试绣现有 v002 三款

1. 阅读 [设备操作指南](docs/operator-guide.md)，本轮使用 **CHENILLE-REF-v002**。
2. 进入 [v002 方案与交付目录](releases/reference-guided/v002/README.md)，完整下载目录或解压 `CHENILLE-REF-v002-operator-kit.zip`。
3. 用本地浏览器打开目录根部的 [index.html](releases/reference-guided/v002/index.html)，选择款式查看逐针回放、对照图和对应候选 DST。
4. 在 Wilcom 检查后安排试绣，复制对应款目录内的 `trial-record.json` 填写；每款、每次重复单独记录。操作方不需要安装 Python。

首批包含 Bulldogs / Font2（328.9 × 98.7 mm）、Bulldogs / Font3（329.7 × 97.6 mm）、Cougars / Font3（319.9 × 108.3 mm）。状态均为文件验证通过，待 Wilcom 检查与实机试绣。

[v001 历史基线](releases/bulldogs-font2-330/v001/README.md) 保留作对照，另见 [v001 操作指南](docs/operator-guide-v001.md)。`scripts/package_operator.py` 仅打包 v001；本轮请领取文件名明确含 `CHENILLE-REF-v002` 的交付包。ZIP 存于本地 `dist/`，默认不纳入 Git。

## 目录

```text
chenille-embroidery-digitizer/
├── assets/private/          # 原始 DST、字体、订单 PDF，保留原路径
├── library/                 # 版本索引、人工标注、覆盖报告
│   ├── catalog/v001/
│   ├── annotations/
│   └── coverage/v001/
├── rules/                   # 字体连接规则、软件策略与工艺配置
│   ├── fonts/
│   └── processes/
├── orders/                  # 订单/生成记录模板及本地工作区
├── experiments/             # 逐轮假设、变更、证据与决策
├── src/chenille/             # 统一引擎；已实现样本索引
├── scripts/                 # 命令入口及历史生成脚本
├── configs/                 # 样本库及候选运行配置
├── examples/                # 最小可复现案例
├── tests/                   # 编码、交付及索引回归检查
├── feedback/                # inbox、reviewed、templates
├── releases/                # 冻结交付；原 v001/v002 路径保持不变
├── build/                   # 临时候选，不进入 Git
├── dist/                    # 操作方交付包，不进入 Git
└── docs/                    # 目标、操作说明、结构与迭代方案
```

见 [目录职责与每轮工作流](docs/repository-layout.md)。开发方从 [样本索引](library/README.md) 开始；订单和新词组合引擎尚待实现。


## 开发方快速开始

先核对样本索引：`python scripts/index_library.py --version v001 --verify`。原库变化后以新的版本号构建索引，详见 [索引说明](library/README.md)。

v002 生成步骤和环境见 [v002 复现说明](releases/reference-guided/v002/README.md#文件与复现)。以下命令针对 v001 历史基线；其中打包命令不会生成 v002 交付包。

基线环境：Python 3.13（本次验证为 3.13.13）。激活虚拟环境后执行下列跨平台命令，详细 Windows / macOS 步骤见 [开发说明](docs/developer-guide.md)。

```sh
python -m pip install -r requirements.lock.txt
python -m unittest discover -s tests -v
python scripts/verify_release.py
python scripts/build_pilot.py
python scripts/package_operator.py
```

`build_pilot.py` 只写入 `build/bulldogs-font2-330/`。生成器会拒绝覆盖 `releases/`；发布新版本需要审查新输出并建立新的版本目录。当前案例无需私有 PDF、完整字体或样本库即可复现 DST；私有 Font2 存在时才额外渲染字体参考图。

## 持续迭代约定

通用版本采用 [样本库驱动路线](docs/library-driven-roadmap.md)：优先匹配并复用已有完整 DST，再扩展字母、数字及连接组合。已有输出范例与新词生成分别验证；检索和组合引擎仍待实现。

最新整理：[50 份人工针路对照分析](feedback/reviewed/path-comparison-50-20260930/README.md)（2026-10-13）。这批为字体中线生成候选的数字对照，尚无实机结果，且与已发布 Bulldogs v001 为不同生成版本。

- 用版本 ID + DST SHA256 绑定每次试绣，记录软件/机器端缩放、旋转及另存操作。
- 每轮只验证一个主要假设，保留失败记录和旧版本。
- 将“文件验证通过”“试绣完成”“操作方接受”分开记录；不能因文件校验成功就标为可生产。
- 改进必须注明适用字体、材料、装置与设置。完整方案见 [迭代方案](docs/iteration-plan.md)。
- 已交付版本不原地替换；实际反馈存放在版本目录外。

## Git 内容范围

原始资料保留在 `assets/private/`。当前其中已有文件被 Git 跟踪，不能因目录名含 private 就认为已排除；本次结构调整保留现有跟踪状态。新增实际订单放 `orders/local/`，待整理反馈放 `feedback/inbox/`，两者按 `.gitignore` 管理。仓库中保留用于复现基线及 v002 的最小 DST 样本、对照输入和生成成果。这里没有为原始字体或样本附加开源许可。详见 [资料与上传说明](docs/data-policy.md)。

上传前可执行 `git status --short` 和 `git ls-files --others --exclude-standard` 检查待提交文件。不要使用 `git add -f assets/private` 绕过默认范围。远程仓库地址、访问权限和首次推送由项目所有者配置；本次整理没有推送到任何远程服务。
