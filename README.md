# A-buildchecker 云主机实验

本目录是可运行的教学参考实现，已合并 E6/E7 代码，未包含助教门禁演示测试。
请先阅读实验包 docs/00_开始与目录.md，再按 02_A轨道操作指南.md 完成步骤。
统一入口：`python3 scripts/lab_cloud.py --help`。
不需要 Windows、WSL、Docker Desktop，不使用助教的学号、代理地址或宿主机目录。
仓库旧 Makefile/Compose 属于 E4 环境接口；本次优先使用 lab_cloud.py，避免镜像标签混用。


## E13–E14 主责集成

入口与范围见 [labs/e13e14](labs/e13e14/README.md)，组员步骤见 [操作说明](docs/e13-e14/teammate-guide.md)。本轮的交叉测试、教师项目、四服务和缺陷证据见 [231880138 报告](docs/students/231880138/e13-e14/report.md)。候选是否可发布以 [发布门禁](docs/e13-e14/release-candidate.md) 为准；不把本地彩排当作 B12 签收。
