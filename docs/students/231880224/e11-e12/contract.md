# E11/E12 接口契约核对

- 报告版本：`schema_version=e11e12-1`；每阶段包含 `kind`、`commit`、`job_id`、`trace_id`、`status`。
- 基线 `full-check` 属于 base_commit；`incremental-check`、`repair`、`recheck` 属于 target_commit。
- MDFixer 输入取自本轮 `incremental-check.json`，由 result 中的 artifact SHA256 校验；外层 commit 与内层 `data.commit` 必须指向目标提交。
- artifact URI 为 `artifact://job-id/相对路径`；下载时核对响应头 `X-Content-SHA256` 与清单一致。
- 同一幂等键同一输入返回同一 job_id；同键不同输入返回 409 `IDEMPOTENCY_CONFLICT`。
- 任务状态：QUEUED、RUNNING、SUCCEEDED、FAILED、TIMED_OUT；服务重启后未完成任务标 `SERVER_RESTARTED`。
- 入口仅在 127.0.0.1 绑定，本次使用 8082；跨机联调通过 SSH 转发。
