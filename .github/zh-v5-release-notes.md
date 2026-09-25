{pack_mb} MB 中文包（原 v3-31-1 为 44.9 MB，会让 Clink 崩溃）：{rows} 个 reading、{words} 个词、{pairs} 条下一词转移，按 Swift 字典开销估算常驻内存约 {resident_mb} MB。

决定 iOS 是否杀掉键盘扩展的是常驻内存，不是文件大小：一行光是字典 key 和数组的固定开销就约 64 字节，之后每个候选才 16 字节。

预算主要花在 CIME 上，因为只有它决定一个词能不能打出来。CIME 与 CLEX 是相互独立的两张表——Clink 官方 zh 包里也只有 61.9% 的 CIME 候选在 CLEX 中（首位候选 63.4%），所以候选不需要 CLEX 里有对应词条。CLEX 只承担词频辅助和 CNGM 的词 ID，每个词约占 50 字节常驻内存，因此用 `max_clex_words` 把它压到接近官方包的规模，省下的内存全部换成 CIME 的 reading 行。

保留原候选顺序、全部单音节、简拼、中英混输、自维护快捷词和领域词，万象全部错音错字纠错（cuoyin）、自维护常见误读，以及参考搜狗 / libpinyin 的拼音按键纠错（如 zhognguo、nihoa、tain）。`lue`／`nue` 这类 ü 误拼与它们本身也能切分成的正常拼音（lu+e）合并，正字在前、原候选保留。不含英文拼写纠错。zh.cngm 按最终 zh.clex 的词 ID 重新生成。
