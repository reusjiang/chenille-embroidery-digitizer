# 可复用规则

已交付试用规则：[codex-trial-v001](releases/codex-trial-v001/README.md)，含确定的执行约束、固定校验和记录模板。下列字体/工艺目录仍为研究和规则积累区域，不自动成为已接受生产规则。

- [fonts/](fonts/README.md)：字母笔段、进出位置、回走、交叉和连接规则。
- [processes/](processes/README.md)：起收、采样及设备/材料适用配置。

规则描述可复用行为；`configs/` 选择本轮使用的规则与参数；`experiments/` 保存修改及接受依据。状态可使用 proposed、tested、accepted、deprecated。tested 必须注明是文件测试还是实机测试；accepted 必须限定适用条件。

目前没有已接受的通用字体连接规则。v002 软件参数仅作为可追溯的初始实验配置，不是已验证工艺。现有生成器尚未自动读取这里的新规则，后续接入时必须通过回归验证。
