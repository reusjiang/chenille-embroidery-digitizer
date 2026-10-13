# 命令入口

| 入口 | 用途 |
|---|---|
| `index_library.py --version v001 --verify` | 核对样本索引快照及所有原始 DST 哈希 |
| `index_library.py --version v002` | 在原库更新后生成新的索引快照，拒绝覆盖已有版本 |
| `build_feedback_candidate.py --output build/<new-name>` | 生成既有 v002 三款同词参考候选 |
| `build_pilot.py` | 生成 v001 Bulldogs 基线候选 |
| `verify_release.py` | 校验 v001 发布清单 |
| `package_operator.py` | 生成 v001 操作方包 |

均从仓库根目录以 `python scripts/<入口>` 运行。新通用逻辑放 src/chenille/；旧脚本及其文件路径暂时保留，以保证原案例复现。索引工具写 library/ 的新快照，其余针迹生成工具仍只写 build/。
