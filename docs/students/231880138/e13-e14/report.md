# E13–E14 主责与个人实验报告

王备中 · 231880138 · A12 · A 轨道 · 2026-11-25 更新

状态：本人的代码、测试和材料已准备；**B12 实际回包、反向签收及其 CI 记录已核验归档，尚待 A12 获准合并和候选发布**。李玄同的历史 APPROVE 因后续文档提交在平台失效；功能源码未变，不将历史审查写成当前有效批准。B 回包归属徐泽宇，不计为王备中个人执行。

## 身份、版本与贡献

- A12 仓库：https://github.com/mechadrug/devops-1020-a12
- 分支：`codex/e13-e14-231880138`；主责 PR：https://github.com/mechadrug/devops-1020-a12/pull/18
- 最终功能代码：`f8f23ec2ebe7eff7adb37b437e1005458039524b`。之后的个人报告提交只增加文档；课程包的源码快照 SHA 以 `provenance.json` 为准，并检查功能文件没有漂移。
- B12 实现：https://git.nju.edu.cn/devops2026fall/devopsB12 ，固定 `main` 提交 `4950f610a47dbbbf08731eb42c0c621326745ca8`。B12 的 DRAFT、MDFixer 原字节模块在 `labs/e13e14/vendor/`，文件摘要在 `B12_SOURCE.json`；没有合并 B 仓库历史。
- 服务器：`/root/231880138/e13-e14/candidate`；原始错误基线独立保存在同级 `buildchecker/work/baseline`。
- 运行镜像 `course-e11e12:231880138`，实际 ID `sha256:32e192f709badf97d39f075b7a7e1ab7b727d3e1711cf1d9a2d8ec26eabad508`。四角色启动使用该完整 ID；DRAFT 每个候选的实际构建 image_id 另保存在其 iter-02/image-inspect.json。

本次主责工作包括：接入课堂 E13/E14 增量模板；维护 A12 交换项目和输入包；固定实际 B12 两个组件；补交接哈希保护、非 root 部署身份与长任务健康检查；新增 7 项本人测试；运行三个教师项目、B12 项目 C1–C8、四服务和故障恢复；组织交接、PR 与材料归档。13 项旧契约测试保留，E13 测试共 10 项（课堂 3 项 + 本人 7 项），Windows 与 A12 Linux 均通过。课堂代码、丁的公共集成和 B12 实现不冒写为本人独立开发。

## E12 补充基线

丁宏业的 `/root/devops-submissions/231880397/E11-E12-A12-B12-cross-20261117.tar.gz` 保存了在 A12 服务器挂载 B12 源码进行的 A→B→A 代码级消费。其报告明确 B12 自有服务没有直接消费该 job。相关说明和结果以贡献归属保存在 `work/team-e12-supplement/`；本次重新独立执行，不把该归档当作本人 E13 日志。

## 交换项目与来源

|提供方|项目及改动|base / target|
|---|---|---|
|A12 王备中|Policy offset：新增 CLI 参数校验、8 项行为测试和 helper 的间接策略头文件依赖|`892e18910c27f2f1f5a105880c1f4e36c79f9494` / `9c312e412e6c3efb3dbed3b3fd4db50afccfb52e`|
|B12 徐泽宇 241276010|Reading Window：命令行读数统计，C1 引入下限头文件而未声明依赖；来自 B12 仓库 evidence/E11-E12/241276010/real-project|`77466fc787b21046641f088dc82b0bcd3e72add5` / `1cb95780bce185c11570ca0bc2096fd9ca687ac9`|

A12 项目保留课程双源构建形状，但有独立修改和测试，不是原样生成样例。生成器固定测试仓库的提交元数据和时间以重现 SHA，实际运行时间以原始日志为准。B 项目的原 bundle、dataset 和候选保留；两者均保存完整项目历史，不将工具仓库 SHA 当成目标项目 SHA。项目默认输出 1，VALUE 改为 2 后输出 2。输入范围为当前双 C 源文件、明确 Make 规则的教学接口。

已经制作 `A12-E13-交给B12.zip`，包含当次 A 报告、项目历史、原始图/trace、候选和接收说明。`consume_on_b.py` 会验证整个交接清单及 A 报告身份，再调用接收者自己 B 仓库的 DRAFT/MDFixer。本次在 A12 使用真实 B12 源码进行的脚本彩排为 SUCCEEDED，执行者明确为 231880138；**不算 B12 远端签收**。2026-11-24 已收到徐泽宇 241276010 的真实回包，其成功 job 为 `job-701fd0d1231c402a8adcba5cc4f73b01`，8 项行为测试通过，685 个产物清单引用独立核验通过。B 工具提交 `1fc3728c2d10e840f502c5f30716e69b31a551ca` 的两个核心模块与 A 固定副本逐字节一致；外层 pipeline 不假定相同。11 月 25 日从 B12 远端发现其正式反向签收与 pipeline 358293 记录，执行/CI/发布版本的相关模块字节一致；无需继续等待群回复。CI 结论来自 B12 已提交的正式记录，主责未登录其 CI 页面，详见 [截止核查](../../../e13-e14/deadline-status.md)。

## C1–C8：在 B12 实际项目上的本人运行

证据主目录 `work/final/C1-C8-B12-complete/`。八项本地结果均通过。原始运行时的 `local-results.json` 中 `remote_B12_signoff=PENDING` 保持原样，最新真实回包与剩余反向签收状态见 `B12回包核验.md`，不回写旧日志。

|用例|实际观察|证据|
|---|---|---|
|C1|A 全量/增量一致；本地消费者取同轮 A 报告并修复通过；两个版本 make test 通过|C1-A、C1-local-consumer、两个 behavior.log|
|C2|用真实 C0 另跑生成旧报告，向 C1 消费，STALE_REPORT；拒绝发生在 DRAFT 前|C2-baseline-report、C2-rejected|
|C3|有效 JSON 追加换行且沿用原 SHA，ARTIFACT_HASH_MISMATCH|C3-hashes.json、C3-rejected|
|C4|单任务 0.01 秒上限，外层 FAILED、内层 TIMED_OUT；任务构建客户端/运行容器无残留|C4-timeout、C4-processes、C4-containers；宿主最终进程/容器快照另存|
|C5|行为失败与无效补丁均 accepted=false、rollback=true；原库 HEAD、所有跟踪文件哈希与状态前后一致|C5-test-rejected、C5-invalid-rejected、C5-source-state.json|
|C6|测试副本假值脱敏命中退出 1，清理后退出 0；假值不入源码历史或镜像|C6-hit、C6-clean、C6-hashes；全范围扫描见下文|
|C7|错误 base 失败后正常任务成功；job/trace 不同，成功产物 URI 和哈希独立|C7-failed、C7-recovery|
|C8|真实 HTTP 同键同输入同 job，异输入 409；E12 五阶段成功，报告与补丁下载字节/响应头/清单 SHA 一致|C8-api，任务 `job-d85cbe65f13c46c0a506538d3b66af70`|

## 教师发放的三个项目

项目是固定上游源码的课程适配副本，保留 UPSTREAM.md、许可、原始源码和项目 bundle；不是原封不动地验收完整上游工程。

|项目|课程 base|课程 target|最终结果|
|---|---|---|---|
|H1-jsmn|`66a6dafcc20cea76bf017923d3db725d78407845`|`948a1d30cd758d32d45a50f788e5a95fb1d89c69`|五阶段 SUCCEEDED|
|H2-inih|`aafc740a2cac05a74541abede93b7d59ed23b87f`|`3aadb81763c79651e4dfa99b725ba921ee2b8a39`|五阶段 SUCCEEDED|
|H3-tiny-aes|`dc8099306d7023b7337328d718149973e7b17978`|`5640bb69a01e64559207e9f74d15a9ae71a4d0f3`|五阶段 SUCCEEDED|

jsmn 首次通过；inih 与 tiny-AES-c 首次在依赖下载阶段超过原定 600 秒，原始 FAILED/TIMED_OUT 目录保留在 `baseline/`。没有将下载故障判为算法正确或算法缺陷。复测候选只改下载源 TUNA→Aliyun，并将新增工具安装 RUN 放到 COPY 前复用缓存；保持原 FROM digest、COPY、make/CMD 和项目完整 SHA。原/新候选摘要与修改理由在 `work/candidate-adaptations.json`，最终请求和日志位于 `work/final/H*/`，均实际完成五阶段并接受补丁。最后一轮教师项目的源码身份记录于 `work/final/source-sha.txt`；此后相关 pipeline、scan/patch/validate、DRAFT 源码未变。

## 缺陷闭环

|Issue|修复前|修复与回归|状态|
|---|---|---|---|
|[#17](https://github.com/mechadrug/devops-1020-a12/issues/17)|基线 `5120d2dc4e81331fbc70575a152d2f5b5b820c7a` 忽略 fixed_report_sha256，坏哈希输入真实运行竟然成功|读取前校验摘要与内外 commit，启动构建前拒绝并在消费边界复查；同一坏输入现退出 1 / ARTIFACT_HASH_MISMATCH|修复已验证，等待 PR18 审查合并后关闭|
|[#19](https://github.com/mechadrug/devops-1020-a12/issues/19)|GitHub runner 的宿主 checkout 与容器强制 root 身份不同，EChecker 因 Git dubious ownership 返回 422|Compose 显式继承宿主 UID/GID；DRAFT 单独补 Docker socket 组；不取消 Git 归属保护；实际非 root CI 复测成功|同上|
|[#20](https://github.com/mechadrug/devops-1020-a12/issues/20)|长 DRAFT 阻塞单线程 HTTPServer 的 /health，容器 unhealthy；回归用例复现超时|并发 HTTP 健康请求 + 每角色写操作锁；单测和真实长构建期间 24/24 健康请求成功，最大 16.67 ms|同上|

执行器开发过程中还保留了缺少 ps、目录重名和初次使用镜像默认 UID 的失败记录。最终改用 /proc、任务 job 唯一目录和明确运行身份，完整矩阵重新运行，不删除失败目录。

## 四服务与恢复验证

这是开发分支上的部署验证；E13 整体签收未齐，未据此发布正式 RC。最终证据为 `work/final/e14-verified/`，四角色分别经 HTTP 工作：A12 BuildChecker/EChecker、固定 B12 DRAFT/MDFixer。共享课程镜像与工作目录，只有 DRAFT 挂载 Docker socket，端口仅 127.0.0.1:18081–18084。每服务 1 CPU、768 MiB、128 PID，实际配置与 inspect 均保存。

|运行|job_id|trace_id|结果|
|---|---|---|---|
|sample|`job-c4374a23d27041a8b350403087cdacb9`|`trace-a8662218ec504cc499417bb9a041b2cb`|SUCCEEDED|
|A12-policy|`job-9170fe3a2e864aae937f864cb0b59c75`|`trace-6bc64cfdf0ee4ff9a5d53a19b1dd1882`|SUCCEEDED|
|B12-reading-window|`job-7397b7722fb14a06b9493abb5b97baf2`|`trace-dbe67e1450574273a0aaf021f93e0880`|SUCCEEDED|
|timeout-recovery|`job-609a629880e940b09eb2a7f82f803d1b`|`trace-f49af841d1ab4c79a5f73c027f2707c7`|SUCCEEDED|
|service-recovery|`job-13d2f12672364ea48a17f2c40f471dd2`|`trace-78e1105beda148e9a0cc8046f7e83b1f`|SUCCEEDED|

另外两项受控故障：DRAFT 超时导致整次 FAILED，恢复原请求后新 job 成功；仅停止本次 Compose 的 EChecker，另一次任务定位连接拒绝，恢复该服务后新 job 再次五阶段成功。两次错误均独立保留。复验等待 Docker 健康状态实际变为 healthy 后才取恢复快照，保留此前过早采样为 starting 的记录。四服务日志可按每个 job/trace 找到四个角色的状态和耗时。

候选报告经内容哈希进入 MDFixer，accepted=true，动态复验无 MD，RD 如实保留。真实额外 RUN sleep 8 的健康探针另存 `work/final/health-probe*`：24 次 HTTP200，任务仍在运行时健康接口保持响应。最终仅关闭本人 Compose 项目，原共享 8081 服务仍可用。

## 扫描、环境与独立核验

源码/历史/镜像构建历史与环境变量、镜像 /app 与 /opt 应用目录、全部本人运行日志均检查通过；C6 只用假值且已清理。无 .env 或凭据进入提交与课程包。独立核验脚本检查了 **5382 个产物清单条目**（包含复测的重复条目，不是测试用例数）、阶段 commit/job/trace、四角色日志关联、资源/端口/挂载和故障恢复。

宿主 2 CPU、3.5 GiB RAM、约 59.8 GiB 可用空间。原 doctor 的 4 GiB 最低阈值未满足，退出 1；没有把环境自检写成通过。实际功能与资源限制验证完成，未出现 OOM。此项保留为分配主机的容量限制。

## CI 与发布门禁

功能提交 `f8f23ec2ebe7eff7adb37b437e1005458039524b` 的真实 PR 检查全部成功：

- E7：https://github.com/mechadrug/devops-1020-a12/actions/runs/45131147486
- E8–E10：https://github.com/mechadrug/devops-1020-a12/actions/runs/45131147517
- E11–E12：https://github.com/mechadrug/devops-1020-a12/actions/runs/45131147508
- E13–E14（contracts + four-services）：https://github.com/mechadrug/devops-1020-a12/actions/runs/45131147467

源码快照所对应的最终文档 head 检查另放在课程包 ci/；源码与功能提交的差异只允许本次文档。CI 原始 ZIP 摘要与 GitHub digest 一致，首次失败日志也保留。B12 提供的对应代码 CI 为 `54ab7ca8a6c029360ae1512e35404b4e9a2acf19` / pipeline 358293；独立核对其 lab.py、autobuild.py、pipeline.py 与实际执行版本完全一致。CI 的 success 是 B12 提交记录，不声称已直接观察其私有 GitLab 运行页面。

李玄同已对 `1aed823…` 正式 APPROVED，审查链接及非阻断建议见回包核验。本次文档更新不改变功能代码。B12 反向签收和对应 CI 记录已收齐；PR18 未合并，Issue 17/19/20 未在平台流程关闭。未创建或移动 v0.9-rc。完整状态、复现与回退预案见 docs/e13-e14/release-candidate.md。课程包可用于审阅当前成果，补齐交接/审查/合并与候选发布记录后应重建最终提交版本。
