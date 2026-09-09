# Clink Community zh — controlled IME probe

This is a diagnostic release, not production Wanxiang v3. Read the release
title/tag for the variant: **B = pin → 榀**, **A = pin → 拼**.
Only publish the other variant after recording the current iPhone test.

## 本轮怎么试（先试 B）

1. 记下 Clink 的完整 App 版本/build；不用仅写“最新版”。
2. 在 Clink 的 Languages 中，停用/移除已安装的 Official 中文和旧 Community
   中文（包括 zh_wx）。只操作语言资源；先保留自己的布局、设置和学习记录。
   如果界面无法移除或无法区分来源，请截图，不要猜它已清除。
3. 在 General → Repositories 中刷新本仓库；若仍显示旧版本，可移除再重新添加
   https://github.com/dayifulalala-del/clink-language-packs 。
4. 在 Languages → Community 安装本仓库的中文 zh。
   核对本次 Release tag（以 B 或 A 结尾）；如 UI 不显示 tag，截图来源和包详情。
   若仍只显示 zh_wx，本轮尚未取到新的中文 manifest，先不要继续测词频。
5. 确认当前语言为这份中文；保持同一 Pinyin 布局，不同时启用另一份中文。
   关闭并重新打开 Clink 和测试用的备忘录。若仍旧，可重启 iPhone 后复测。
   这些是重载尝试，**不保证清除 App 私有缓存**。
6. 新建空白文本，逐键输入 p、i、n，**停在 pin，不按空格、不选候选**。
   B 包的 CIME 此行只有“榀”（木字旁加“品”）；A 包只有“拼”。
   截图完整候选条以及正在组合的原文。不要选中/学习这些测试候选。
7. 清空后分别输入 pinyin 和 pin yin，各截一张图。
   这两行文件中的首选仍是“拼音”，但运行时是否查整行、分段或用空格上屏尚未确认。
8. 发回：pin 候选截图、安装来源/版本截图、Clink 版本/build。
   记录是否启用学习/预测；若界面有开关，可以在测试前关闭并保持状态不变。
   不要求删除用户词典，不要求删除整个 App。

**判定：** B 出现“榀”在首位是支持新数据参与的信号；下一轮只换 A，
若同样步骤的 pin 首选随之变为“拼”，再换回 B 又恢复“榀”，才有更强的
Community CIME 因果证据。单次没出现不等于“必然仍加载官方表”。
“已安装”、下载次数和 Actions 成功都不是实机通过。

“榀”故意用于诊断，不是正常词频优化。生产版会撤掉这一修改。
旧 pinyin → 万象验证 / pin → 万象 的不等音节指纹已停用；未确认 App
允许这种映射，不能用它不出现来证明加载失败。

## Exactly what is shipped

Only code zh, with zh.cime, zh.clex and zh.cngm; plus the release manifest.
No official neural model, BPE vocabulary, emoji or other-language assets.

The baseline is the immutable, SHA-pinned historical v2 release
[vzh-wx-v2-1-1](https://github.com/dayifulalala-del/clink-language-packs/releases/tag/vzh-wx-v2-1-1).
Its complete CLEX/CNGM pair is retained byte for byte and named zh; neither
format embeds a language code. All CIME rows except pin are also unchanged.
This is a controlled delta, not a tiny three-word dictionary.

| Asset | Bytes | SHA-256 |
|---|---:|---|
| zh.clex, both variants | 5,779,667 | 541fa81f34bcaabd68813936cc446be3410ea1837a828f252af8557a9217ecd8 |
| zh.cngm, both variants | 7,616,460 | e08dbdac24732c9dab12640bad973f63ecadaeb597aa831a3aa21e98dbb0f243 |
| zh.cime, A | 7,962,119 | 9e3762faffd6e386dec5ee784a8bd027852e9edfb0572fa119ea1c091c5c1ae4 |
| zh.cime, B | 7,962,119 | 6ebf2005d305be4fe41e15e3d7b03ffa12ad500f0713df3f0afda2dd8c358f6b |

The builder verifies 403,280 CLEX words, 300,000 readings, 846,272 CNGM pairs,
all candidate membership, complete binary offsets, word ID bounds and the
one-row A/B difference. Word-ID semantics are preserved by keeping the matched
v2 pair unchanged, not merely by checking bounds. The total size is still
about 21 MB; runtime memory limits and model influence are not established.

The published manifest follows the upstream generator unchanged. It has no
invented locale, inputMethod or priority fields. The workflow checks both
GitHub releases/latest and releases?per_page=1, re-downloads all assets, and
checks releases/latest/download/manifest.json against its build result.
These checks rule out specific distribution errors, not iPhone caching.

To verify a particular published tag:

```shell
python3 tools/zh_ime_probe.py verify-release --version TAG_FROM_RELEASE --variant B
```

A variant can be selected through the workflow's Run workflow control. The
normal push path publishes B only. v1/v2 workflows remain manually available;
their old releases and production resources are preserved.

## Attribution / CC BY 4.0

Derived from [Rime Wanxiang](https://github.com/amzxyz/rime-wanxiang) by amzxyz
and contributors, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The v2 baseline used Wanxiang v17.3.0: dicts/jichu.dict.yaml,
dicts/zi.dict.yaml and dicts/lianxiang.dict.yaml. Historical changes include
Pinyin normalization, deduplication, frequency-based candidate selection,
a 16-candidate cap, vocabulary selection and phrase-derived next-word weights.
This diagnostic renames the pack to zh and replaces only the pin row with a
hand-selected, valid one-syllable/one-character candidate.
See WANXIANG_V2.md for historical build provenance.
