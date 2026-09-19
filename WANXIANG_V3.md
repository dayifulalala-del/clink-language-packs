# Clink 中文万象 v3（dict-nightly）

这是已经通过 iPhone 实机指纹验证后的正式 Community 中文包。

## 已确认的 Clink 行为

实机输入 `pinyin` 时，Clink 会把组合串显示为 `pin yin`。受控诊断版把该 reading 的第一候选设为“万象验证甲”后，iPhone 候选栏确实出现了该指纹，因此已经确认：

- Community `zh` 会进入 Clink 的中文 Pinyin IME；
- Community `zh.cime` 确实参与候选生成；
- Clink 会把连续全拼自动切成带空格的音节序列；
- 正式包因此同时保留 compact 与 syllable-spaced 两种 reading key。

正式版已经删除所有“万象验证甲/乙/丙”诊断候选。

## 上游数据

本包每次构建都直接下载万象滚动预览 Release：

- Upstream: https://github.com/amzxyz/rime-wanxiang
- Release tag: `dict-nightly`
- Asset: `base-dicts.zip`
- License: CC BY 4.0（遵循万象上游署名和许可要求）

`dict-nightly` 是滚动更新的预览版，因此同一个 tag 的内容会随着上游更新而变化。每个 Clink Release 都附带 `wanxiang-source.json`，记录实际使用的 upstream release ID、发布时间、asset SHA-256，以及所有参与构建的词典文件 SHA-256，便于复现。

## 使用的完整 nightly 中文词表

v3 以 `base-dicts.zip` 实际内容为准，而不是假设仓库分支上的每张表一定被打进 Release。核心 `zi / jichu / lianxiang` 必须存在；其余中文 `*.dict.yaml` 只要出现在当前 rolling asset 中就全部纳入。

当前构建会自动排除 `abbrev / t9_abbrev / en / mixed` 这几类不适合作为 Clink 中文 CIME 主数据的表。像 `cuoyin / duoyin / shici / diming / yixue / huaxue / yaopin / mingren / yiren / taifeng / fangyan` 等，只要 nightly 包里存在就会自动加入；如果上游未来重新加入 `wuzhong / renming` 或新增中文表，也会自动纳入并记录到 receipt。

## Clink 适配

万象原始词库规模远大于 Clink 官方中文包；直接不加限制地塞入 iOS 键盘扩展会造成不必要的体积和内存压力。因此 v3 是“完整 nightly 中文数据源 + Clink 高信号裁剪”，而不是把每个长尾 reading 原样复制进去：

- CIME：最多 400,000 个高信号 reading；
- 每个 reading：最多 16 个候选（Clink 自身上限）；
- CLEX：最多约 600,000 个高信号词，并强制保留全部汉字和实际进入 CIME 的候选；
- 最长候选：16 个汉字；
- 同时生成 compact 与带空格全拼 reading；
- 极低频、生僻、扩展区单字只降权，不用官方旧表那种异常顺序；
- CLEX 与 CNGM 使用同一份最终词表，避免 ID 不匹配；
- 不携带 Clink 官方旧 neural model，避免旧模型与新词典混用。

## 必过回归

正式 Release 只有在以下第一候选全部正确时才发布：

- `pinyin` / `pin yin` → `拼音`
- `nihao` / `ni hao` → `你好`
- `meiyou` / `mei you` → `没有`
- `zenme` / `zen me` → `怎么`
- `zenmehuishi` / `zen me hui shi` → `怎么回事`
- `weishenme` / `wei shen me` → `为什么`
- `buzhidao` / `bu zhi dao` → `不知道`
- `keyi` / `ke yi` → `可以`
- `xianzai` / `xian zai` → `现在`
- `jintian` / `jin tian` → `今天`
- `mingtian` / `ming tian` → `明天`
- `zhongwen` / `zhong wen` → `中文`
- `shurufa` / `shu ru fa` → `输入法`
- `suoyi` / `suo yi` → `所以`

另外：

- `pin` 前 5 个候选不得出现 `穦`；
- Release 中不得出现任何“万象验证”诊断候选；
- manifest 只能发布一个 `zh` 包；
- 只发布 `zh.cime / zh.clex / zh.cngm` 三个语言资产，不混入官方旧神经模型。


## 中文键盘中的常用英文与保守纠错

v3 还带一份人工维护的 `source/zh-latin-terms.tsv`。目的不是把整套英文词典硬塞进中文 IME，而是让中文键盘里常见的品牌、开发工具和技术词能直接正确输出，并给少数高价值词提供保守的 typo alias。

例如：

- `github` → `GitHub`
- `chatgpt` → `ChatGPT`
- `codex` → `Codex`
- `openai` → `OpenAI`
- `iphone` → `iPhone`
- `docker` → `Docker`
- `python` → `Python`
- `xcode` → `Xcode`

并包含少量明确的常见误拼：

- `githbu` → `GitHub`
- `chatgtp` → `ChatGPT`
- `codxe` → `Codex`
- `doker` → `Docker`
- `pyhton` → `Python`

正确英文词也会进入 CLEX，使 Clink 自身的 spelling help 有词典依据。App 内部的通用自动纠错算法不属于语言包，因此 v3 不会给 40 万拼音 reading 暴力生成模糊拼写；这样能避免中文候选被大量错误 alias 污染。
