# Chenille Embroidery Digitizer

雪尼尔刺绣打带与实机反馈迭代项目。当前提供一个可复现的 **Bulldogs / Font2 / 330 mm** 试生成案例，基于人工同词 DST 的笔顺重建路径。尚未实现任意订单 PDF 自动打带，也尚未完成 Wilcom / 大豪设备试绣验收。

## 设备操作方从这里开始

1. 阅读 [设备操作指南](docs/operator-guide.md)。
2. 进入 [BULL-F2-330-v001 交付目录](releases/bulldogs-font2-330/v001/README.md)。
3. 下载或完整解压目录，双击 `replay.html` 看逐针回放；Git 网页通常只显示 HTML 源码，需要本地浏览器打开。
4. 在 Wilcom 检查后，用目录内的 `Bulldogs_F2_330mm.DST` 试绣，并填写 [试绣反馈表](feedback/templates/trial-report.md)。操作方不需要安装 Python。

| 基线指标 | v001 |
|---|---|
| 状态 | 文件验证通过，等待实机试绣 |
| 落针路径实际尺寸 | 330.0 × 99.0 mm |
| 普通落针 / 跳针命令 | 786 / 0 |
| 起 / 收回线实测弧长 | 9.998 / 9.981 mm，包含圆弧 |
| 待重点观察 | 两端短针、内部尖转、回走重叠效果 |

完整试绣包由开发方运行 `python scripts/package_operator.py` 生成于 `dist/`。该 ZIP 不纳入 Git，可作为 Git 平台的 Release 附件或直接交给操作方。

## 目录

```text
chenille-embroidery-digitizer/
├── README.md
├── docs/                         # 操作指南、开发说明、打带要求、迭代方案
├── examples/bulldogs-font2/       # 最小可复现人工 DST 样本及来源校验
├── releases/bulldogs-font2-330/
│   └── v001/                     # 冻结 DST、回放、预览、报告、校验清单
├── feedback/
│   ├── templates/                # 操作方反馈表和结构化记录
│   ├── reviewed/                 # 经整理、可共享的实际试绣记录（目前没有）
│   └── inbox/                    # 本地待整理反馈，不进入 Git
├── scripts/                      # 生成、回放、报告、校验、交付包工具
├── tests/                        # DST 编码/回读及交付完整性测试
├── requirements.txt              # 直接依赖
├── requirements.lock.txt         # 已验证的依赖版本集合
├── assets/private/               # 本地订单、完整样本库、字体、设备照片，不进入 Git
├── build/                        # 自动生成候选，不进入 Git
└── dist/                         # 操作方交付 ZIP，不进入 Git
```

## 开发方快速开始

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

- 用版本 ID + DST SHA256 绑定每次试绣，记录软件/机器端缩放、旋转及另存操作。
- 每轮只验证一个主要假设，保留失败记录和旧版本。
- 将“文件验证通过”“试绣完成”“操作方接受”分开记录；不能因文件校验成功就标为可生产。
- 改进必须注明适用字体、材料、装置与设置。完整方案见 [迭代方案](docs/iteration-plan.md)。
- 已交付版本不原地替换；实际反馈存放在版本目录外。

## Git 内容范围

原始订单含客户联系/地址信息；完整样本库、字体和设备照片保留在 `assets/private/`，由 `.gitignore` 排除。仓库中保留了用于复现本案例的单个人工 DST 和生成成果。这里没有为原始字体或样本附加开源许可。详见 [资料与上传说明](docs/data-policy.md)。

上传前可执行 `git status --short` 和 `git ls-files --others --exclude-standard` 检查待提交文件。不要使用 `git add -f assets/private` 绕过默认范围。远程仓库地址、访问权限和首次推送由项目所有者配置；本次整理没有推送到任何远程服务。
