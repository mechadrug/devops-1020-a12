# E13/E14 交接与运行契约

A 输入提供完整 base/target、项目历史、候选来源/摘要、行为测试与限制。工具仓库 SHA、目标项目 SHA 和镜像 ID 分开记录。

handoff_a_to_b 核验 result 的成功 schema、target、唯一增量阶段、job/trace、内外 commit 及引用产物的 bytes/SHA，然后生成 fixed-md 信封并保留 source_report。E11-B 如有 fixed_report_sha256，读取字节前验证；错误 SHA、旧 commit、类型错误均拒绝，不手工改 commit。

E14 四角色 /v1/run 消费工作目录中的任务副本；MDFixer 核对增量报告 SHA 和 schema/kind/status/commit/job/trace。Compose 与宿主编排共用 UID/GID；工作输入放 data、输出放新的 work 子目录。健康请求不等待角色写锁，写操作串行。

异步 /v1/jobs 保留同键同输入复用、异输入 409 的规则。E12 API 下载的报告与补丁均核对响应头、清单及实际字节。artifact URI 是任务内相对位置，不是另一台主机可直接读取的本地路径。

consume_on_b 验证交接清单后，记录实际接收者 Git 身份与 B 源码 SHA，调用其原有模块并产生 receipt。VALIDATED_ONLY 不代表构建成功；A12 以 231880138 彩排的 SUCCEEDED 也不是 B12 签收。最终共同记录必须包括 B 本人的执行/证据与 A 检测结果签收。
