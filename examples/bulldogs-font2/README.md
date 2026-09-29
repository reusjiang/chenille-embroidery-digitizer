# Bulldogs / Font2 人工参考样本

`source.DST` 是原始样本库中 Font2 Bulldogs 的逐字节副本，用于复现当前生成器。它不是交给操作方上机的试生成文件。

- 原宽约 328.9 mm，808 条普通落针命令，零跳针。
- 主路径边界：原第 6–802 针，当前算法仅适用于这份经过核对的样本。
- 原始字节 SHA256 与来源范围见 provenance.json。
- 完整样本库本地保存在 assets/private/dst-library/，默认不进入 Git。

Font2 对照为 Loverine。生成器复用已有人工中心路径；不依赖字体文件推导新字母，也未实现任意单词拼接。
