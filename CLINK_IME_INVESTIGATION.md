# Clink Community 中文 IME 公开实现调查

> **2026-09-09 更正：** 下面保留早期调查背景；涉及旧三词指纹的充分性和手机清理状态的
> 断言已撤回。旧实验同时改变多项资源，且使用音节与字数不一致的映射，阴性结果不能
> 证明官方文件仍活跃。`zh_wx` 硬编码问题仍未知。GitHub `releases/latest` 和列表首项曾
> 返回不同 tag，显式设 Latest 也不足以消除分发歧义。现行协议、证据边界与复测步骤以
> [FINGERPRINT_TEST.md](FINGERPRINT_TEST.md)、[BLACKBOX_TEST_PLAN.md](BLACKBOX_TEST_PLAN.md)
> 和修订后的 [UPSTREAM_ISSUE.md](UPSTREAM_ISSUE.md) 为准。

调查日期：2026-09-08。本文只把公开代码和公开产品说明当作事实；没有公开实现支持的
结论都标为推断或待实机验证。

## 调查范围

已逐一检查 `anti-ltd` 组织当时公开的全部 `clink-*` 仓库：

- `clink-actions`
- `clink-fonts`
- `clink-index`
- `clink-language-packs`
- `clink-layouts`
- `clink-localizations`
- `clink-panels`
- `clink-profiles`
- `clink-sounds`
- `clink-themes`
- `clink-themes-tf`
- `clink-themes-unofficial`

检查项包括 README、JSON/YAML、构建脚本、Release workflow、manifest、历史提交、Release 历史、
GitHub issues 和 pull requests，并对用户指定的关键词做了全局搜索。在当时的公开仓库中，
除 `clink-themes` 有一个与字母垂直对齐无关的已关闭 issue 外，没有找到 IME、Chinese、
Pinyin、Community language pack 或 `.cime` 加载机制的 issue/PR 说明。

`anti-ltd` 的公开仓库列表中没有 Clink iOS App 核心源码仓库。`clink-index` 只是上述内容仓库的
索引和 Git submodule 集合，不包含运行时资源选择代码。

## 公开代码确认

### Language Release manifest

`tools/build-release-manifest.py` 生成的顶层只有：

```json
{"version":"...","packs":[...]}
```

每个 pack 的公开字段只有：

- `code`
- `version`
- `assets`
- 可选 `neural`，仅描述模型格式和训练数量

每个 asset 只有 `path`、`url`、`sha256`、`byteCount`。manifest 里没有公开的
`languageCode`、`locale`、`inputMethod`、`pinyin`、`profile`、`layout` 或候选排序字段。

pack 由 `<code>.clex` 发现；它是必需资源。生成器再收集同前缀的 `<code>.*` 资源。
Release asset 名为 `<code>--<logical-path-with---separators>`，但 App 实际应根据 manifest 中的
`path` 恢复逻辑文件名。资源名、版本、大小和 SHA-256 都会影响资源身份或完整性验证；
但 App 如何判断“已安装版本需要更新”没有公开代码。

### `.cime`

`tools/build-ime-table.py` 把每行编译为纯 UTF-8：

```text
reading<TAB>candidate-1<TAB>candidate-2...
```

构建器小写化 reading、对候选去重、保留输入顺序，并在每个 reading 截止到 16 个。
它不编译成二进制，也不加入 IME 类型 metadata。

官方 `zh.cime` 的关键行是：

```text
pin  -> 穦, 拼, 品, ...
yin  -> 因, 音, 印, ...
```

该文件没有 `pinyin` 或 `pin yin` 整行，却有 `nihao -> 你好`、`meiyou -> 没有`、
`weishenme -> 为什么`、`zhongwen -> 中文` 等部分连续多音节 reading。

### `.clex` 和 `.cngm`

`build-pack.py` 写出 CLEX v1，按 UTF-8 字节顺序存放词条。`tools/build-next-word.py` 在完全相同的
词序上使用数字 word ID 写出 CNGM v1。因此替换 CLEX 却保留旧 CNGM 确实会让 ID 错位。

官方 README 把 CNGM 定义为 next-word model，把 `.cime` 定义为 reading-to-character 表。
公开代码不包含 App 中将 CIME 候选和 CLEX/CNGM/neural 分数合并的部分。

### Community 与官方资源

官方 README 确认：Community pack 在 **Languages -> Community** 中以单独来源显示；每个仓库的
内容保持独立。下载先进 staging，只有所有大小/SHA/类型验证通过且 `.clex` 存在时才激活；
失败则保留上一个已验证 pack。

这些说明没有回答同一 `code=zh` 同时存在官方和 Community 时，键盘运行时选择哪一份。
`clink-localizations` 的 README 明确写了同码 locale 由官方优先，但 language-pack README 没有同样的
说明，因此不能把 localization 的优先级直接当作 language pack 的事实。

### Profile、layout 与 index

- 公开 `.clinkprofile` 只有 `id`、`name`、`icon`、`config`；现有 profile 没有语言字段。
- 公开 `.clinklayout` 示例只有 `id`、`name`、`rows`；没有 language code 或 IME 字段。
- `clink-index` 只索引内容仓库，没有语言 catalog、显示名、IME 类型或同码优先级表。
- App Store 1.3 的公开更新说明称“添加语言会自动选择合适 layout”，同时产品说明把
  Chinese Pinyin 列为内置输入方式。公开资源里无对应关系表，所以这个关联应在未公开的 App 层。

## 根据资源格式和实机结果推断

### `pin yin` 和连续 `pinyin`

实机出现 `穦因`，恰好是官方 `pin` 行第一候选 `穦` 加 `yin` 行第一候选 `因`。
而所检查的官方表中没有 `pin yin` 整行。这与以下假设相容，但没有证明：

- 带空格输入可能按音节分段，然后组合每段的 `.cime` 候选。
- “每个 reading 保留候选顺序”与“多音节整句看起来被重排”并不矛盾：前者只描述单行，
  后者可能是多行的动态组合。

对不带空格的 `pinyin`，App 是先做最长整行 lookup，还是先分成 `pin` + `yin`，仍未由公开资源确认。
`BLACKBOX_TEST_PLAN.md` 的 D 实验使整行和分段返回不同指纹，可直接判定。

### 为什么 `zh_wx` 安装后不变

待验证假设，不是公开代码事实：Clink 的 Pinyin 组合器或 Pinyin layout 映射识别已知语言代码
`zh`，而 `zh_wx` 只是一个可下载的普通字典代码。证据是：

- manifest 没有其它字段能把 `zh_wx` 声明为 Pinyin。
- profile/layout 也没有这种声明。
- 官方简体中文 Pinyin pack 的实例代码是 `zh`。
- 安装 `zh_wx` 成功只能证明通用 pack 校验通过，不能证明 Pinyin 组合器已使用它。

### v1 和 v2 Release 的额外风险

- v1 虽然发布 `code=zh`，但同时携带官方 `zh.clex`、`zh.cngm`、`zh.bpevocab` 和官方旧
  `zh.mlmodelc`。这不是干净的 CIME 加载实验。
- v2 发布后成为该仓库的 latest Release，其 manifest 只有 `zh_wx`。如果 Clink 只发现 latest
  Release manifest，新安装时就不会再发现旧 Release 里的 v1 `zh`。公开 App 代码不存在，
  所以“只读 latest”仍是根据文档和所有 Release workflow 的强推断。
- 旧 fingerprint Release 显式设为 latest，只有 `zh.clex + zh.cime`；但后续发现列表首项
  仍为另一版本，所以不能说已经消除了分发混淆。其三词 CLEX 本身也新增了兼容性变量。

## 仍必须由 iPhone 回答的问题

1. Community `zh` 能否成为当前中文 IME 的真正资源来源。
2. 官方和 Community 同码 `zh` 的选择和优先级。
3. 安装目录、缓存 key、旧资源删除范围和强制重下载触发点。
4. 连续拼音、空格分节、模糊拼音的具体 lookup 路径。
5. CLEX 词频、CNGM、neural model 和个性化学习是否及何时重排 CIME 候选。

当前采用保留完整词典的合法一音节 A/B 指纹，见 FINGERPRINT_TEST.md；在实机候选随
Community CIME 受控变化以前，不进入正式万象 v3。旧“万象验证”协议不再用作加载判据。

## 主要公开来源

- https://github.com/anti-ltd/clink-language-packs
- https://github.com/anti-ltd/clink-language-packs/blob/main/tools/build-ime-table.py
- https://github.com/anti-ltd/clink-language-packs/blob/main/build-pack.py
- https://github.com/anti-ltd/clink-language-packs/blob/main/tools/build-next-word.py
- https://github.com/anti-ltd/clink-language-packs/blob/main/tools/build-release-manifest.py
- https://github.com/anti-ltd/clink-index
- https://github.com/anti-ltd/clink-layouts
- https://github.com/anti-ltd/clink-profiles
- https://github.com/anti-ltd/clink-localizations
- https://apps.apple.com/us/app/clink-custom-keyboards/id6776381848
