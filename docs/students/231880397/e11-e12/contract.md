# E11/E12 接口契约核对

- 报告版本：`schema_version=e11e12-1`；每阶段有 `kind`、`commit`、`job_id`、`trace_id`、`status`。
- 基线 `full-check` 属于 base_commit；`incremental-check`、`repair`、`recheck` 属于 target_commit。
- MDFixer 输入为本轮 `incremental-check.json`，由 result 中的 artifact SHA256 校验；commit 和内层 data.commit 必须指向目标提交。
- artifact URI 为 `artifact://job-id/相对路径`；下载时核对 `X-Content-SHA256`。
- 同一幂等键同一输入返回同一 job_id；同键不同输入返回 409 `IDEMPOTENCY_CONFLICT`。
- 入口仅在 127.0.0.1 绑定；跨组通过 SSH 转发。
