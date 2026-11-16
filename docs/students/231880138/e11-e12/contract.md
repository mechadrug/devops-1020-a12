# E11–E12 A 侧个人交付契约

版本 e11e12-1。消费请求包含 mode、repo、完整 base/target SHA；E12 另含 candidate、expected_output、build_timeout。容器内路径位于 /course/data。生成样例和组内适配项目的请求分别保存，不混用提交。

阶段封装必含 schema_version、kind、status、commit、job_id、trace_id、data、artifacts。full-check commit 对应 base；incremental-check、draft、repair、recheck 对应 target。封装 job/trace 贯穿同一任务，组件嵌套 trace 可保留独立运行身份。封装和 data.commit 不一致时拒绝为 STALE_REPORT，错误 schema、上游失败和错误类型分别拒绝。

产物引用为 artifact://<job_id>/<相对路径>，含 sha256 和 bytes。下载端用 /v1/jobs/<job_id>/files/<相对路径>，X-Content-SHA256、清单摘要与实际内容一致。load_artifact 在解析内容前校验摘要，内容变化拒绝为 ARTIFACT_HASH_MISMATCH。

API：POST /v1/jobs 使用 idempotency_key 和 input；同键同输入返回同 job_id，同键不同输入 HTTP409。GET 查询任务和 /artifacts 清单；未准备好清单返回409。服务恢复已完成任务身份，未完成持久状态标记 SERVER_RESTARTED。本人实测服务使用 127.0.0.1:8082，组内原服务为 8081。

E12 修复消费本轮 incremental-check，最终 patch_applies/build/test/header_change/no_missing 均为 true、动态重检无 MISSING；REDUNDANT 可以保留。完整 job/trace、URI 与摘要在运行目录和 integration.csv 中。
