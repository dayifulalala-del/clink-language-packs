# Clink 中文万象 v2

这不是对官方 `zh` 包的覆盖，而是一个独立语言代码：`zh_wx`。

更正（2026-09-09）：独立代码不保证进入 Pinyin 引擎，也不保证不会回退。
下面的回归测试验证的是发布文件中的候选顺序，不是 iPhone 候选。历史 v2 保留供复现；
当前受控 `zh` 诊断版见 `FINGERPRINT_TEST.md`，不能把 v2 与旧三词指纹版称为字节等价测试。

## 为什么改成 zh_wx

测试发现 Clink 官方 `zh.cime` 的 `pin` 行本身就是：

`穦 / 拼 / 品 / ...`

用户安装第一版 Community `zh` 后，实际候选仍然出现“穦因”，说明与官方 `zh` 使用相同语言代码时存在资产冲突或回退风险。v2 因此不再覆盖 `zh`，而是发布完全独立的 `zh_wx`，用来验证 Clink 是否真正加载 Community 的 CIME。

## v2 同时重建

- `zh_wx.cime`：万象拼音候选；同时生成 `pinyin` 与 `pin yin` 两种 reading key。
- `zh_wx.clex`：万象词频词典，不再使用官方中文词频。
- `zh_wx.cngm`：从万象高频词/短语生成加权中文字符与词组转移模型。
- **不携带官方神经模型**：避免旧模型继续用旧中文数据重排候选。

## 数据来源

Wanxiang / Rime 万象拼音 v17.3.0（构建固定使用 release tag `v17.3.0`，对应发布提交 `296f90d`）。
Upstream: https://github.com/amzxyz/rime-wanxiang
License: CC BY 4.0 (按上游许可与署名要求使用)。

## 回归测试

构建必须保证：

- `pinyin` → `拼音` 第一候选
- `pin yin` → `拼音` 第一候选
- `nihao` / `ni hao` → `你好`
- `meiyou` / `mei you` → `没有`
- `zenmehuishi` / `zen me hui shi` → `怎么回事`
- `pin` 前 5 个候选中不得出现 `穦`

只有全部通过才发布 Release。


## 体积控制

IME reading 表默认限制在 300,000 个高信号 reading，避免把万象全部长尾词条无上限塞进 Clink；常用回归词会强制保留。
