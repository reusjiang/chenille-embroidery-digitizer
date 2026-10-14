# 设备操作指南

如果要用自己的 Codex 处理本地 PDF 新订单，请先读 [START_HERE.md](../START_HERE.md) 和 [Codex 操作指南](codex-operator-guide.md)。以下步骤只适用于直接试绣既有 v002 三款。

**本轮请进入 [CHENILLE-REF-v002 版本目录](../releases/reference-guided/v002/README.md)**，试绣 Bulldogs / Font2、Bulldogs / Font3、Cougars / Font3 三款候选。文件检查已通过，尚待 Wilcom 检查和实机试绣。

v001 保留为历史基线；只有明确安排 v001 对照试绣时，才使用 [v001 操作指南](operator-guide-v001.md)。

## 1. 领取并确认版本

完整下载版本目录，或解压开发方提供的 `CHENILLE-REF-v002-operator-kit.zip`。打开版本目录或解压目录根部的 `index.html`，选择对应款式查看回放、对照图并下载 DST。操作方无需安装 Python。

| 款式 / 回放 | 本轮候选 DST | 落针路径尺寸 mm | 落针 / 跳针 |
|---|---|---|---|
| [Bulldogs / Font2](../releases/reference-guided/v002/01-F2-Bulldogs/replay.html) | `Bulldogs_F2_328.9mm_v002.DST` | 328.9 × 98.7 | 829 / 0 |
| [Bulldogs / Font3](../releases/reference-guided/v002/36-F3-Bulldogs/replay.html) | `Bulldogs_F3_329.7mm_v002.DST` | 329.7 × 97.6 | 810 / 0 |
| [Cougars / Font3](../releases/reference-guided/v002/43-F3-Cougars/replay.html) | `Cougars_F3_319.9mm_v002.DST` | 319.9 × 108.3 | 687 / 0 |

每款子目录内的 `comparison.png` 是人工参考、旧候选与本版的对照图，`returns.png` 是起收局部图。仓库 `examples/` 和交付包 `reference-inputs/` 内的文件仅为对照输入，本轮候选使用上表文件。

DST 的 SHA256 校验值：

- `Bulldogs_F2_328.9mm_v002.DST`：`743229434795721c452ff21bfa6d83f137fc2abdc649c804c93752f6822e4f0a`
- `Bulldogs_F3_329.7mm_v002.DST`：`a34a44bbddd09fe33e6d9d67dc98f588fd59153cf2b66d0b2ba57996ef7a0211`
- `Cougars_F3_319.9mm_v002.DST`：`96376889f67a9dadecb4fe8c4e6f40212f48f47f0b1aa32b001acc40c3ff102d`

也可在各款 `validation.json` 查看校验值。在 Windows PowerShell 切换到 DST 所在目录后执行（其他款替换文件名）：

```powershell
Get-FileHash .\Bulldogs_F2_328.9mm_v002.DST -Algorithm SHA256
```

哈希不相同表示文件内容已变化，先记录实际版本并让开发方核对。

## 2. Wilcom 核对

在现用 Wilcom EmbroideryStudio e4.2 中打开文件，记录是否正常导入，以及显示的宽高、针数和方向，并与上表核对。各款包含一条起点零位移命令；不同软件统计口径若有差异，请保留截图。

检查 Bulldogs 的 B 回环、双 l 谷底、d/g 连接，Cougars 的 o/u 过渡和 g 回环，以及三款起收回线。最短非零针距分别约 0.100、0.141、0.200 mm，需核查实际设备能否适用。当前 DST 没有机型专属毛巾绣/链式绣模式切换指令，也没有原生 EMB；请核对设备工作模式。

若另存、缩放、旋转、镜像或修改针迹，保留实际使用文件及其校验值，记录改动，不能把结果记作未修改 v002 的效果。

## 3. 首轮试绣

使用操作方现有适用的设备设置，记录机器、控制器、机头/装置、工作模式、转速和张力，以及面料、衬料、毛线、针具和装框方式。

每款先做两次同条件重复。出现异常时按现场操作规程处理并记录，不为凑次数继续运行。

重点检查起针稳固性、收针露尾或松脱、掉头堆线，以及内部尖转、回走和交叉处外观。三款起收区域针号不同：

| 款式 | 起针回线 | 收针回线 |
|---|---|---|
| Bulldogs / Font2 | 1–10 | 821–829 |
| Bulldogs / Font3 | 1–10 | 798–810 |
| Cougars / Font3 | 1–10 | 679–687 |

以上为各款 `stitches.csv` 的针号。机器显示编号可能不同；无法对应时记录字母和位置并拍照即可。记录短针附近是否发生故障，但不要仅凭针短就认定根因。

## 4. 拍照和测量

至少拍全图正面和问题部位近照；必要时补背面及故障视频。尽量正对面料、均匀照明，比例尺与面料处于同一平面，圈出问题位置。照片避免包含客户地址、面单等无关资料。

在绷尺寸、放松后尺寸分开记录，并写明放松等待时间。上表尺寸是落针路径范围；记录测量对象是落针中心还是毛线外缘。三款保留各自人工稿宽度，并非统一 330 mm。

## 5. 回传反馈

复制对应款目录的 `trial-record.json` 填写，它已绑定款式、版本和 DST 校验值；未知项保持 null。也可使用 [文字反馈表](../feedback/templates/trial-report.md)，将版本与文件信息填写为本轮实际款式。

每次重复使用独立的试绣 ID，例如：

```text
CHENILLE-REF-v002_01-F2-Bulldogs_YYYYMMDD_01/
├── trial-record.json
├── front-overall.jpg
├── start-closeup.jpg
├── end-closeup.jpg
└── problem-01.jpg
```

通过双方约定渠道回传目录或压缩包。原始待整理资料放本地 `feedback/inbox/`，开发方整理至 `feedback/reviewed/<trial-id>/`。反馈另存，不写入冻结版本目录。

每轮记录完成情况、断线及停机次数、问题位置、照片、当前设置和操作方判定。文件验证通过不等于实机合格；未试绣的模板也不是验收记录。

## 6. 收到下一版

确认新版本号和变更说明，保持约定条件比较指定部位，保留旧版与失败样片。三款首批候选以外的 47 款尚未重新生成。后续版本只有完成试绣并经操作方确认，才能记录适用条件内的接受结论。
