# Clink 中文万象 v5 compact

## 为什么选择本仓库后 Clink 会崩溃

v3-31-1 的 zh 包一共 44.9 MB，是官方 zh 包的约 40 倍：

| 文件 | 官方 zh | v3-31-1 | v5 compact |
|---|---|---|---|
| zh.cime | 0.5 MB / 2.8 万 reading | 20.4 MB / 65 万 reading | 4.0 MB / 11 万 reading |
| zh.clex | 0.4 MB / 3 万词 | 14.5 MB / 93 万词 | 3.8 MB / 25 万词 |
| zh.cngm | 0.4 MB | 9.9 MB（ID 错位） | 2.3 MB |

iOS 对键盘扩展的内存限制只有几十 MB。按普通 Swift 方式把 v3-31-1 的 `zh.cime`
读成 `[String: [String]]`，本机实测仅这一个文件就要约 80 MB，超过限制后键盘进程会被系统直接杀掉。

另外 v3-31-1 的 `zh.cngm` 与 `zh.clex` 词 ID 不一致：CNGM 按 932,800 个词编号，
而 `build-pack.py` 会丢掉带空格或不含字母的词（如 `app store`、`+86`），CLEX 只剩 932,658 个。
于是所有下一词联想都指向错误的词，还有 87 条指向词典末尾之外。

## v5 做了什么

`tools/compact_zh_pack.py` 以已验证的 v3-31-1 资产为输入，只删行、不改顺序：

- 保留每一行原有的候选顺序、每个词原有的 CLEX 词频字节；
- 全部单音节、`source/` 下的快捷词 / 领域词 / 品牌英文、回归用例一律保留；
- 与官方表格式一致：reading 只含 a-z，去掉 `pin yin` 这类带空格的重复键和打不出来的数字键；
- 中文按词频保留 8 万个 reading，英文 / 品牌 / 纠错另留 3 万个（完整英文词优先于纠错别名）；
- 多音节行最多 10 个候选（单音节保留全部 16 个）；
- `zh.cngm` 按最终 CLEX 的词 ID 重新生成，规则与 `build_zh_wanxiang_v2.py` 相同。

用官方 zh 词典里 2.5 万个真实高频中文词衡量「前 5 个候选里能打出来」的比例：
v3-31-1 为 93.17%，v5 为 92.45%。

## 发布与调参

推送 `tools/compact_zh_pack.py` 或 `.github/workflows/build-zh-wanxiang-v5-compact.yml`
会自动发布新的 latest（`vzh-wanxiang-v5-z…`，版本号排在所有 v3/v4 之后）。

如果仍然崩溃，在 Actions → *Publish compact Clink Chinese Wanxiang (v5)* → Run workflow
里把 `max_readings` 调到 60000 或 40000；稳定后也可以往上调。workflow 会拒绝发布超过
15 MB（或 CIME 超过 6 MB）的包。

`build-zh-wanxiang-v3.yml` 仍会直接发布未裁剪的 65 万行大包，不要再手动运行它。
