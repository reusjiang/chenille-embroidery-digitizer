# 软件策略与工艺配置

[v002-software-baseline.json](v002-software-baseline.json) 引用 v002 已冻结的几何参数及校验值，便于后续实验追踪；参数唯一原件仍为 `configs/feedback-v002.json`，避免维护两个独立数值副本。

这些针距、半径和回线值尚未按设备与材料完成验收，不是通用工艺标准。[process.template.json](process.template.json) 用于另建经试绣验证的工艺配置。配置必须注明机器、装置/模式、材料和尺寸范围，未知值保持 null。
