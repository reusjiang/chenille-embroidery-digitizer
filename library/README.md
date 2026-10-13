# 样本库工作区

原始文件继续存于 `assets/private/dst-library/`，这里保存索引和标注，不复制或改写原始 DST。

- [catalog/v001/catalog.json](catalog/v001/catalog.json)：按完整 SHA256 标识样本，同字节内容合并为一个样本，保留所有来源路径。
- [catalog/v001/manifest.json](catalog/v001/manifest.json)：索引与覆盖报告校验值、生成代码和配置哈希、环境信息。
- [coverage/v001/summary.json](coverage/v001/summary.json)：数量、重复内容、异常待查及文件名字符线索。
- [annotations/](annotations/README.md)：人工标注、已确认文字及笔段来源；与自动索引分开维护。

## 创建和检查

从仓库根目录运行：

```sh
python scripts/index_library.py --version v001 --verify
python scripts/index_library.py --version v002
```

第二条在原库变化后创建新快照；已存在版本会拒绝覆盖。索引构建需要 requirements 中的 pyembroidery。构建不会调用生成器，也不修改原 DST。字体目录别名在 [配置](../configs/library-index.json) 中维护。

`sample_id = dst-sha256-<完整 SHA256>` 标识字节内容，文件改名不改变 ID；修改针迹产生新 ID。同一内容可能有多个来源及字体线索，应保留并核对，不能默默选取。

`text_hint` 仅来自文件名，`font_id_hint` 仅来自目录映射；`verified_design`、`machine_acceptance` 未经核对保持 null。索引中的可解码状态不是严格文件校验，更不是自动生产授权。零宽/零高、非标准结束等进入检查列表，不直接删除。

v001 快照不自动吸收后续标注。人工核对结果按样本 ID 与 SHA256 另存，未来匹配器需显式合并这些记录；当前还没有订单匹配器或新词组合器。
