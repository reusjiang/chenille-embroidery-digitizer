# 样本标注

标注独立于自动索引保存。通过完整 `sample_id` 和 `source_sha256` 绑定内容；不得仅凭路径或名字绑定针号。

[annotation.template.json](annotation.template.json) 提供字段约定。核对图形后填写真实文字、字体和排版；笔段以 1 起始的 STITCH 命令编号描述，若需引用跳转等命令，必须另行写明编号口径。非连续笔段使用多个范围。

[v002-source-selections.json](v002-source-selections.json) 迁入既有 v002 的三款主路范围和来源证据，属于同词重建选段，不是已完成的字母切分，也没有新增实机结论。原 v002 配置及发布文件保持不变。

模板复制为新文件再填写。草案不得被当作已接受规则。样本修改后重新标注，不沿用旧针号。
