# 231880398 real-project fixture

A12 仓库 `fixtures/md-rd` 的双源显式 Make 适配，用于 231880398 的 E12 真实项目联调。
这不是外部生产项目；来源与提交见 `docs/students/231880398/e11-e12/requests/real-dataset.json`。
C0 保留 main.o→config.h 缺失和 unused.h 冗余；C1 在 helper.c 引入 config.h，
同时让 helper.o 规则漏写 config.h，形成新的增量缺失。
