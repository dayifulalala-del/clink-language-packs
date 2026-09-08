# Clink 中文万象增强包

这是给 Clink 中文拼音输入使用的增强 `zh.cime` 构建层。

## 设计目标

- 直接改善“输入拼音后候选词太少、排序太差”的问题。
- 使用万象基础词库、单字库、成语库。
- 保留 Clink 官方中文 `zh.clex` / `zh.cngm` / 神经模型。
- 自动通过 GitHub Actions 构建并发布 Clink 可安装的 GitHub Release。
- Release manifest 只发布 `zh`，不会把 fork 里的其他语言重复显示为 Community 包。

## 为什么第一版只替换 zh.cime

Clink 的 `.cngm` 使用与 `.clex` 字节序词表对应的数字索引。直接重建 `zh.clex` 却继续使用旧 `zh.cngm` 会造成索引错位。因此 v1 只增强拼音候选表，这是最直接、风险最低的改动。

## 安装

GitHub Action 成功发布第一个 Release 后，在 Clink：

`General → Repositories → 添加 owner/repository`

然后到 `Languages → Community` 安装中文包。
