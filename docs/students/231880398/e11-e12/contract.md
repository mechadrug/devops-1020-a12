# E11/E12 接口契约核对（231880398）

- 外层报告版本固定为 `schema_version=e11e12-1`；每个阶段包含 `job_id`、`trace_id`、`kind`、`commit`、`status`、`data`、`artifacts`。
- `data` 内部仍为 E8–E10 的 `e8e10-1`；外层 `commit` 与 `data.commit` 都必须指向本阶段 commit，任一不一致返回 `STALE_REPORT`。
- `full-check` 属于 `base_commit`；`incremental-check`、`repair`、`recheck` 属于 `target_commit`。
- MDFixer 只消费本轮 `incremental-check` 报告；报告由 result 中的 artifact SHA256 定位，不能直接信任未校验路径。
- artifact URI 为 `artifact://job-id/相对路径`；下载文件时校验响应头 `X-Content-SHA256` 与清单 SHA256。
- 同一幂等键、同一输入返回同一 `job_id`；同键不同输入返回 HTTP 409 `IDEMPOTENCY_CONFLICT`。
- 文件接口拒绝 `.git`、越界路径和不存在的 job，统一返回 404 `NOT_FOUND`。
- 服务器重启时，`QUEUED`/`RUNNING` 任务变为 `FAILED`，错误码 `SERVER_RESTARTED`；`SUCCEEDED` 任务仍可查询。
- API 只绑定回环地址；跨主机 A/B 交换需要 SSH 转发。本轮未做跨主机交换。

## 本轮核对结果

| 契约点 | 证据 |
|---|---|
| 外层/内层版本与 commit | `work/e12-231880398/full-check.json`、`incremental-check.json`、`recheck.json` |
| artifact SHA 与相对 URI | `work/e12-231880398/result.json`、`work/api-e12-231880398/artifacts.json` |
| 同键不同输入 409 | `work/api-e12-231880398/conflict.status` / `conflict.json` |
| 路径穿越 404 | `work/api-e12-231880398/traversal.status` / `traversal.json` |
| 旧报告 `STALE_REPORT` | `work/e11-b-stale-231880398/result.json` |
| 服务器重启规则 | `labs/e11e12/test_231880398.py` |
| 文件 SHA 响应头 | `work/api-e12-231880398/patch-headers.txt` |
