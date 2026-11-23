# v0.9-rc 候选发布记录

负责人王备中 231880138，A12，2026-11-23。**状态：候选待发布。没有创建、推送或移动标签。**

|对象|固定值或状态|
|---|---|
|集成仓库|https://github.com/mechadrug/devops-1020-a12 ，PR18 开放，尚未合并|
|A 功能代码|`f8f23ec2ebe7eff7adb37b437e1005458039524b`；文档 head 见课程包 provenance.json|
|B 实现|https://git.nju.edu.cn/devops2026fall/devopsB12 ，`4950f610a47dbbbf08731eb42c0c621326745ca8`|
|教学运行镜像|`sha256:32e192f709badf97d39f075b7a7e1ab7b727d3e1711cf1d9a2d8ec26eabad508`，各 DRAFT 产物镜像分别见 iter-02/image-inspect.json|
|E13|本人 C1–C8 8/8、教师项目 3/3；B12 实际消费/签收仍待完成|
|E14 开发分支验证|固定样例、A 项目、B 项目及两类恢复共 5 个成功任务；受控超时和单服务不可用按预期失败；健康探针 24/24|
|CI|A 功能提交四套 workflow 成功；最终文档 head 的真实记录放课程包 ci/；B 对应 SHA 的 CI 仍需其确认|
|缺陷|17/19/20 修复已验证，等待 PR18 审查/合并关闭流程|
|审查/发布|同伴 Review、合并 SHA 和发布批准待完成；未选择正式标签目标|

## 复现和定位

使用本人学号克隆固定源，构建 E11/E12 镜像，准备共享样例和实际交换项目。按 teammate-guide.md 配置 UID/GID、socket 组与四端口。E13 使用 run_matrix.py；E14 使用 orchestrate.py 并保存 Compose state、logs、image inspect、阶段清单与原始 trace。每轮新建 work 子目录，产物核验见课程包 reproduction/verify_cloud_evidence.py。

证据：work/final/C1-C8-B12-complete、work/final/H*、work/final/e14-verified、work/final/health-probe*。完整原始云端归档位于 /root/231880138/e13-e14/，网站 ZIP 将附独立 manifest。A→B 接收脚本本地彩排注明 A12 执行者，不能替代 B 同学回执。

## 已知范围

当前为双 C 源文件和显式 Make 教学配置，三上游项目使用教师适配副本。四角色共享课程镜像和目录；DRAFT 候选镜像运行与下游检测环境分开记载，不宣称通用生产隔离或完全复用候选镜像。只扫描声明的源码、历史、镜像元数据/应用目录和日志范围。旧 doctor 因分配主机 3.5 GiB RAM 低于 4 GiB 返回 1，功能测试和限额验证通过，保留容量限制。

## 回退预案

先保存失败 job、日志、镜像 ID 和 Compose 配置。仅对本人项目执行 docker compose -p e14-<本人学号> down，不停止共享 Docker 或他人服务。需要代码回退时在新的克隆中检出已知可用提交（当前旧 main 8ac17fbde4607eae8a9f336fb6247c67f7bb8644），恢复记录的镜像 ID 和独立端口，再执行契约/样例回归；不改写 main 历史，不重用失败任务目录。此次实际执行的是关闭本人四容器并确认共享 8081 健康，未冒写一次 main 代码回滚演练。

门禁齐备后，由有权限且获准的人在验收的已合并提交创建 v0.9-rc，将最终 A/B/集成 SHA、CI 和证据写进 Release Notes。若同名标签已存在，先核对，不能覆盖。
