# Clink 中文万象 v3（dict-nightly）

这是已经通过 iPhone 实机指纹验证后的正式 Community 中文包，并在此基础上加入全拼、简拼、中英混输、英文纠错、错音容错、现代领域词和长词联想。

## 已确认的 Clink 行为

实机输入 `pinyin` 时，Clink 会把组合串显示为 `pin yin`。受控诊断版把该 reading 的第一候选设为“万象验证甲”后，iPhone 候选栏确实出现了该指纹，因此已经确认：

- Community `zh` 会进入 Clink 的中文 Pinyin IME；
- Community `zh.cime` 确实参与候选生成；
- Clink 会把连续全拼自动切成带空格的音节序列；
- 正式包同时保留 compact 与 syllable-spaced 两种全拼 reading。

正式版不包含任何“万象验证甲/乙/丙”诊断候选。

## 上游数据

每次构建直接下载万象滚动预览 Release：

- Upstream: https://github.com/amzxyz/rime-wanxiang
- Release tag: `dict-nightly`
- Asset: `base-dicts.zip`
- License: CC BY 4.0（遵循万象上游署名和许可要求）

`dict-nightly` 是滚动更新版，同一个 tag 的内容会随上游更新。每个 Clink Release 都附带 `wanxiang-source.json`，记录实际使用的 upstream release ID、发布时间、asset SHA-256、参与构建的词典 SHA-256，以及本仓库自维护词表的 SHA-256。

## 中文主词库

v3 以 `base-dicts.zip` 实际内容为准。核心 `zi / jichu / lianxiang` 必须存在，其余中文 `*.dict.yaml` 只要出现在当前 nightly 中就自动纳入。

当前包含字表、基础词、联想、多音/错音、诗词、地名、医学、化学、药品、名人、艺人、台风、方言等数据。地名、人名和长词额外保留高信号 reading 预算，避免被总表裁剪静默删除。

## 首字母简拼

从万象词条的完整拼音自动生成简拼，例如：

- `bzd` → 不知道
- `wsm` → 为什么
- `zmhs` → 怎么回事
- 高频长词还支持 3 个以上首字母前缀，因此 `zmh` 的前排候选也可出现“怎么回事”

为避免污染正常全拼，如果某个简拼键本身已经是完整拼音、英文或其它明确 reading，则不会用简拼覆盖它。

当前构建最多保留 50,000 个非冲突简拼 reading，每个 reading 仍遵守 Clink 最多 16 个候选的限制。

## 中英混输

除手工维护的品牌/技术词外，正式版会从万象当前 `en.dict.yaml` 中按权重自动选取 20,000 个高频英文词。

例如中文键盘下可以直接得到：

- `computer` → computer
- `github` → GitHub
- `chatgpt` → ChatGPT
- `codex` → Codex
- `iphone` → iPhone
- `docker` → Docker
- `python` → Python

品牌和产品名由 `source/zh-latin-terms.tsv` 保留正确大小写。普通英文进入 CLEX，为 Clink 的 completion / spelling help 提供词典依据。

短英文如果与合法中文拼音冲突，不会粗暴压过中文候选。

## 英文拼写纠错

除人工审核的 typo alias 外，还会对最高频的一部分英文词自动生成两类低风险错误：

1. 相邻字母交换；
2. 漏掉一个中间字母。

生成后会自动删除以下冲突：

- 本身就是正确英文单词；
- 本身是正常中文拼音 reading；
- 与人工维护 alias 冲突；
- 同一个错拼可能对应多个正确单词。

当前构建产生约 2 万个过滤后的自动纠错 alias。例如：

- `githbu` → GitHub
- `chatgtp` → ChatGPT
- `pyhton` → Python
- `compuer` → computer

这不是修改 Clink App 内部的系统级 autocorrect，而是利用 CIME + CLEX 提供确定性的候选纠错，因此更可控。

## 中文错音 / 多音容错

万象 `cuoyin.dict.yaml` 与 `duoyin.dict.yaml` 会直接纳入，而且对应 reading 被列为保护项，不能因为总 reading 数量限制被轻易裁掉。

例如构建回归已经验证：

`maopeifang` → 毛坯房

正常读音仍由主词库负责，错误读音只是兼容入口。

## 中英混合词

正式版同时读取万象 `mixed.dict.yaml`，支持类似中文 + 英文/数字的词：

`githubcangku` → Github仓库

以及上游已有的 3A、QQ、Google 等混合词条。候选显示保留原文本，CLEX 内部使用规范化形式。

## 技术 / 游戏 / 网络 / 流行语

除万象原始数据外，本仓库还维护 `source/zh-domain-terms.tsv` 作为小型高优先级补充层。

目前覆盖：

- 网络与 homelab：软路由、旁路由、分流、直连、节点、内网、端口转发、丢包、延迟、NAS、VPS、SSH、IPv6 等；
- 开发：GitHub、GitLab、API、JSON、YAML、Docker、Python、Swift、Xcode 等；
- 游戏/硬件：显卡、帧率、掉帧、光追、超频、开黑、上分、排位、Steam、FPS、RPG、MOBA 等；
- 网络流行语：YYDS、笑死我了、有一说一、破防、吃瓜、社死、内卷、躺平、摆烂、电子榨菜、显眼包等。

例如：

`ruanluyou` → 软路由

`yyds` → YYDS / 永远的神

## 人名 / 地名

万象 nightly 中的人名、名人、艺人、地名相关表直接参与 CIME，并给这些来源预留额外 reading 预算。

回归示例：

`heilongjiang` → 黑龙江

## 长词与整句候选

`lianxiang` 继续作为长词/长短语来源，并给 5 音节以上 reading 单独预留高信号预算。CNGM 现在也利用最多 16 个汉字的中文短语生成字符和词组转移，不再只看 12 字以内条目。

这能同时改善：

- 直接输入完整长拼音时的整词/整句候选；
- 上屏后的下一词联想；
- 高频长句的简拼入口。

## 当前体积策略

万象原始数据远大于手机键盘实际需要，v3 采用“完整 nightly 数据源 + Clink 高信号裁剪”：

- CIME：最多 500,000 个 reading；
- 每个 reading：最多 16 个候选；
- 自动简拼：最多 50,000 个非冲突 reading；
- 高频英文：20,000 个；
- 英文自动纠错源词：最高频 2,500 个；
- CLEX 基础预算：650,000 个高信号词，实际还会强制保留进入 CIME 的必要词；
- 最长中文候选：16 个汉字；
- CLEX 与 CNGM 使用同一最终词表；
- 不复用 Clink 官方旧 neural model。

当前一次完整构建约得到：

- 500,000 个 CIME reading；
- 约 91 万个 CLEX 词条；
- 约 109 万条 CNGM 转移。

## 必过回归

Release 发布前必须同时通过全拼、简拼、英文、纠错、错音、混输、领域词、地名以及旧垃圾候选回归。核心检查包括：

- `pinyin / pin yin` → 拼音；
- `bzd` 前排包含“不知道”；
- `wsm` 前排包含“为什么”；
- `zmhs` 前排包含“怎么回事”；
- `computer` → computer；
- `compuer` → computer；
- `maopeifang` → 毛坯房；
- `githubcangku` → Github仓库；
- `heilongjiang` → 黑龙江；
- `ruanluyou` → 软路由；
- `yyds` → YYDS / 永远的神；
- `pin` 前 5 不得出现“穦”；
- Release 不得出现任何旧“万象验证”诊断候选；
- manifest 只能发布一个 `zh` 包；
- Release 只包含 `zh.cime / zh.clex / zh.cngm` 三个语言资产，不混入官方旧 neural model。
