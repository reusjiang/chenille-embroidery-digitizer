# 首版软件验证记录

日期：2026-10-14。环境：macOS、Python 3.12.3、pyembroidery 1.5.1。状态：可交付现场试用，尚无 Windows 现场或实机验收。

## 已验证

- 既有 DST、候选、样本索引及交付回归测试通过。
- 规则包测试覆盖 PDF 任务初始化和输入复制、重复 job 拒绝、规则被改动、订单字段未确认/冲突、原 PDF 缺失、候选字节变动、起收范围错误、跳转后逐段回线、缺失实验实现、反馈包重新校验与排除原 PDF。
- 真实执行 verify-rules、search、demo、package；演示候选为已有 v002 Bulldogs / Font2，回读得到 328.9 × 98.7 mm、829 条落针、0 跳针。没有进行 PDF 识别或新词生成。
- 在无 .git 的临时解压目录（包含所需运行文件和演示样本）重复上述四个入口，结果通过。
- 反馈 ZIP 内全部文件哈希通过、引用路径有映射、演示标记保留；重复打包不覆盖旧包。
- 回放脚本语法、文档相对链接、JSON 记录、v001/v002 冻结交付校验通过。

## 现场仍需验证

首次在设备方电脑运行 demo 自检，再用真实 PDF 进行订单字段核对与候选生成。当前规则由 Codex 执行，未提供固定 OCR 或通用字母组合引擎；字段确认、视觉笔顺、圆弧形式和实际工艺效果仍需检查。

本轮没有在浏览器中执行回放交互测试，没有运行 Wilcom，也没有实机试绣。软件通过状态不能作为生产验收结论。

## 维护方复查

```sh
python -m unittest discover -s tests -v
python scripts/operator_trial.py verify-rules
python scripts/operator_trial.py demo --job fresh-demo-id
python scripts/operator_trial.py package --job fresh-demo-id
```

全量测试使用仓库开发依赖；设备方只运行操作工具时按本规则目录 requirements.txt 安装最小依赖即可。
