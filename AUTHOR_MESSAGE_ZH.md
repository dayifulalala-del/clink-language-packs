# 给 Clink 作者的中文说明

作者你好，

我们在尝试用 Community language pack 改进 Clink 的简体中文拼音数据。现在遇到的不是词频或
词库质量问题，而是 Community 中文包虽然能被发现和安装，键盘候选却仍然与 Official
`zh.cime` 完全一致。

我们已经制作了一个只有三项词典、四行拼音映射的最小指纹包。无论 Clink 是整行查询
`pinyin`、查询带空格的 `pin yin`，还是把 `pin` 与 `yin` 分段组合，第一候选都应该明显显示
“万象验证”。实机上没有出现该指纹，仍出现“穦因、拼因”等官方旧表特征。

完整英文最小复现已经整理在：

<https://github.com/dayifulalala-del/clink-language-packs/blob/main/UPSTREAM_ISSUE.md>

指纹 Release：

<https://github.com/dayifulalala-del/clink-language-packs/releases/tag/vzh-ime-fingerprint-1-1>

最希望确认的是：

1. Community 仓库提供同名 `code=zh` 时，是否支持替换 Official `zh`？
2. 语言资源身份是只有 `language code`，还是 `(repository, code)`？同码时谁优先？
3. 中文拼音是否只对某个内置 `zh` 语言实例启用，而不是看到 `.cime` 就启用？
4. 键盘扩展实际从哪里读取当前中文 `.cime`？
5. 官方资源的缓存如何彻底清除，并强制扩展重新打开 Community 资源？

Clink iOS 核心源码没有公开，所以我们没有把这些推断写成事实。只要确认 Community `.cime`
确实能够被当前中文 IME 使用，我们就会继续生成与万象词库匹配的 `zh.cime`、`zh.clex` 和
`zh.cngm`；在此之前不会继续盲目扩大词库。
