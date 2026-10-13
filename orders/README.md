# 订单与生成记录

这里管理“这一单如何生成和交付”，不存放实验结论。订单 PDF 原件继续保留在 `assets/private/orders/`。

- [templates/order.json](templates/order.json)：文字、字体、尺寸、排版以及字段核对状态。
- [templates/generation-record.json](templates/generation-record.json)：输入哈希、样本、规则、生成器和输出的对应关系。
- [local/](local/README.md)：实际订单工作区；新增订单文件默认不进 Git。

每个订单建立 `orders/local/<order-id>/`，保存 `order.json`，每次候选新增 `runs/<run-id>.json`。生成文件仍写 `build/<order-id>/<run-id>/`；完成交付后放入独立的 `releases/<order-id>/<candidate-version>/`，再把路径和哈希回填到生成记录。

`route` 明确填写 exact_reuse、adapt_reference、compose 或 needs_review。直接复用时也记录原样本和输出哈希，两者应一致。机器端另存和变换记录在对应试绣反馈中。

模板是当前字段约定，尚未实现 PDF 解析、订单匹配和自动执行，也没有用 null 字段模拟完成的订单。分享订单前另做脱敏副本；不要把原始联系信息混入公开实验报告。
