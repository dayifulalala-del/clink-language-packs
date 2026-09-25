# Clink 中文万象 v6-lite（dict-nightly lite）

这是万象输入法 Lite 版词库的全量构建：无声调拼音的 14 张词典
（字表 / 基础 / 联想 / 错音 / 多音 / 诗词 / 地名 / 医学 / 化学 / 药品 /
名人 / 艺人 / 台风 / 方言），在此基础上加入全拼、简拼、中英混输、
英文纠错、错音容错和拼音按键纠错。

本 release 是 v6-lite-compact（Fp1）的 known-good 数据源，不直接装机：
全量表约 385 万 readings，常驻内存远超 iOS 键盘扩展的安全线，
compact 流程会把它裁剪到 34MB 红线内再发布。

## 上游数据

每次构建直接下载万象滚动预览 Release 的 lite 资产：

- Upstream: https://github.com/amzxyz/rime-wanxiang
- Release tag: `dict-nightly`
- Asset: `lite-dicts.zip`（`*.lite.dict.yaml`，第二列拼音已去声调，ü→v）
- License: CC BY 4.0（遵循万象上游署名和许可要求）

`dict-nightly` 是滚动更新版，同一个 tag 的内容会随上游更新。每个 Clink Release 都附带 `wanxiang-source.json`，记录实际使用的 upstream release ID、发布时间、asset SHA-256、参与构建的词典 SHA-256，以及本仓库自维护词表的 SHA-256。

上游 `custom/wanxiang_lite.dict.yaml` 声明 16 张表，当前 rolling 资产实际包含 14 张
（物种 wuzhong / 人名 renming 暂缺）；构建脚本自动跳过缺失表，上游补上后会自动纳入。

## 构建说明

- 转换：`tools/build_zh_wanxiang_v2_lite.py`（lite 适配，补齐 ḿ/m̀→me、ň/ǹ/ń→en 等归一化）
- 中间预算：`--max-ime-readings 4500000` / `--lexicon-limit 2600000`
  （实测 385 万 readings / 214 万词 + 20% 余量；v3 的 40 万/60 万预算对 lite 数据会直接 abort）
- 回归探针：67 exact + 7 contains（`maopeifang`→毛坯房、`pinyin`→拼音等）全过才会发布

## 下游

`build-zh-wanxiang-v6-lite-compact.yml`（Fp1：
`--max-readings 178000 --candidate-tiers 6:5,10:3,24:2 --max-following 2`）
从本 release 的 `zh--zh.cime` / `zh--zh.clex` 裁剪出装机包，
常驻内存约 33.2MB（红线 34MB），204,821 readings。
