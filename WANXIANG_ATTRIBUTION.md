# Clink 中文万象增强包 — 数据来源与许可

本仓库的增强中文拼音候选表 `zh.cime` 使用 **万象拼音（Rime Wanxiang）** 的词典数据生成。

- 上游项目：https://github.com/amzxyz/rime-wanxiang
- 使用分支：`wanxiang`
- 固定数据版本：`669d3af7a53a3ec0fd268a82bbeb0b0f948ae944`
- 使用文件：`dicts/jichu.dict.yaml`、`dicts/zi.dict.yaml`、`dicts/chengyu.dict.yaml`
- 万象数据许可：Creative Commons Attribution 4.0 International (CC BY 4.0)
- 许可文本：https://creativecommons.org/licenses/by/4.0/

## 做了哪些修改

原始 Rime 词条被转换为 Clink 的拼音 reading → 候选词格式；拼音被标准化为 Clink 使用的无声调全拼格式；同音候选按万象词频排序；每个 reading 最多保留 16 个候选；Clink 官方原有 `zh.cime` 只作为缺失候选与缺失 reading 的后备覆盖。

本增强包 **不替换** Clink 官方 `zh.clex`、`zh.cngm` 和神经模型资源，以避免词典索引与现有 next-word model 不匹配。

Derived data is based on Rime Wanxiang by amzxyz and contributors, licensed under CC BY 4.0. Changes include format conversion, Pinyin normalization, deduplication, frequency-based ranking, candidate capping, and baseline fallback merging.
