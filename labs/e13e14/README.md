# E13–E14 集成入口

课堂模板接入及 A12 主责改动。运行前阅读 docs/e13-e14/teammate-guide.md，发布状态见 release-candidate.md；当前不是已发布 RC。

- prepare_a12_project.py：重建 A12 独立维护的项目和固定历史。
- handoff_a_to_b.py / consume_on_b.py：核验实际 A 报告并在接收端调用其 B 实现，保留双方身份与摘要。
- run_matrix.py：在课程 Linux 镜像内运行 C1–C8，注明执行者与远端签收待办；镜像内无 ps，使用 /proc。
- service.py / orchestrate.py / compose.yaml：四角色 HTTP，宿主 UID/GID、个人端口、每角色写锁与并发健康请求。
- vendor/B12_SOURCE.json：B12 DRAFT/MDFixer 原字节来源和摘要；A 检测仍用 A12 的实现。
- scan_runtime_logs.py：工作日志独立扫描；源码/历史/镜像检查另用 scripts/secret_scan.py。

任何已有 work/data 都不覆盖；失败记录保留，复测使用新路径。只有 DRAFT 挂载 Docker socket。开发分支自测不是跨组签收，未完成门禁不发布 v0.9-rc。
