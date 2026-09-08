# Community `zh` pack installs, but Chinese Pinyin still uses the Official `zh.cime`

## Summary

I am trying to improve Clink's Simplified Chinese Pinyin data using a Community
language-pack repository. A deliberately tiny `zh` fingerprint pack can be
discovered and installed, but the keyboard does not expose any of its unique
`.cime` candidates. Its output continues to match the Official `zh.cime`.

This is not a request to debug the production dictionary yet. The published
pack contains only enough data to determine which `.cime` Clink actually loads.

Could you clarify whether a Community pack with `code: "zh"` is intended to
replace the Official `zh` pack, and how the active source is selected?

## Minimal public reproduction

- Community repository:
  <https://github.com/dayifulalala-del/clink-language-packs>
- Fingerprint release:
  <https://github.com/dayifulalala-del/clink-language-packs/releases/tag/vzh-ime-fingerprint-1-1>
- Release manifest:
  <https://github.com/dayifulalala-del/clink-language-packs/releases/download/vzh-ime-fingerprint-1-1/manifest.json>
- Successful build:
  <https://github.com/dayifulalala-del/clink-language-packs/actions/runs/34234817397>
- Fingerprint source rows:
  <https://github.com/dayifulalala-del/clink-language-packs/blob/dee34c36114d0c05815bd0854e40e8a637b15810/source/zh-fingerprint-ime.tsv>
- Independent verification script:
  <https://github.com/dayifulalala-del/clink-language-packs/blob/main/tools/verify-published-fingerprint.py>

The release is the repository's latest release. Its manifest contains exactly
one pack, with code `zh`, and exactly two assets:

| Logical path | Bytes | SHA-256 |
|---|---:|---|
| `zh.cime` | 63 | `5e05b6b2a026435b3807db8c99884626f74b6619b6dcf0336286f465e29f2500` |
| `zh.clex` | 98 | `4f985c2b10388f06fd12af2b595beca310ee7668329119a20405e62a439749f9` |

There is no `.cngm`, neural model, BPE vocabulary, emoji metadata, or copied
Official asset in this release.

The entire `zh.cime` is:

```text
pin\t万象
yin\t验证
pinyin\t万象验证
pin yin\t万象验证
```

Therefore all plausible lookup paths have an unmistakable fingerprint:

- direct lookup of `pinyin` -> `万象验证`
- direct lookup of `pin yin` -> `万象验证`
- dynamic composition of `pin` + `yin` -> `万象` + `验证`

The matching CLEX contains only `万象`, `验证`, and `万象验证`, and was built with
the upstream `build-pack.py`. The CIME was built with the upstream
`tools/build-ime-table.py`. The upstream validator passes.

Anyone can verify the published files without checking out the large production
assets:

```shell
python3 tools/verify-published-fingerprint.py
```

## Device procedure and result

The test was performed after removing the previously installed Community
`zh_wx` experiment and attempting a clean Community `zh` installation:

1. Remove installed Chinese entries, including Official Chinese, and remove the
   old Community `zh_wx` entry.
2. Remove `dayifulalala-del/clink-language-packs` from **General ->
   Repositories**.
3. Force-quit Clink and the app used for the typing test, then reopen Clink.
4. Add the repository again.
5. Install its Chinese entry from **Languages -> Community**, without
   reinstalling Official Chinese.
6. Select the Pinyin layout/current Chinese language and type into a fresh plain
   text field.
7. Test `pinyin` and `pin yin` without accepting or teaching candidates.

Expected first candidate for both inputs: `万象验证`.

Observed: the fingerprint does not appear and the candidate behaviour remains
the same as the old Official Chinese data. In particular, `pin yin` continues to
produce candidates such as `穦因` and `拼因` instead of `万象验证`.

This output is a strong fingerprint of the Official table itself: its `pin` row
begins with `穦`, `拼`, `品`, and its `yin` row begins with `因`, `音`, while it
has no exact `pinyin` or `pin yin` row. `穦因` is therefore consistent with the
App segmenting the input and composing the first Official candidates.

An earlier byte-equivalent approach under the independent code `zh_wx` was also
discoverable/installable but did not change Pinyin candidates. Because the
public manifest has no `inputMethod`, `pinyin`, `locale`, `profile`, or `layout`
field, this suggests that IME dispatch is determined elsewhere in the App.

## What the public repositories establish

The public language-pack tooling establishes that:

- `.clex` is required and `.cime` is the optional reading-to-character table
  used for an IME language.
- Community packs are displayed separately from Official packs.
- downloads are staged and the previous verified pack remains active if a new
  pack cannot be activated.
- the release manifest identifies a pack by `code`, `version`, and `assets`, but
  exposes no IME type or source-selection metadata.
- profile, layout, index, and localization repositories expose no mapping that
  can declare `zh_wx` to be a Chinese Pinyin IME.

I could not find a public Clink iOS core repository. I therefore do not want to
present same-code priority, cache keys, install paths, or IME dispatch as known
facts.

Full public-repository investigation:
<https://github.com/dayifulalala-del/clink-language-packs/blob/main/CLINK_IME_INVESTIGATION.md>

## Questions for the App implementation

1. Is a Community language pack with `code: "zh"` supported as a replacement
   for the Official `zh` pack, or are Community packs intended only to add codes
   that are not already Official?
2. Are installed language resources keyed only by language code, or by
   `(repository, code)`? If both Official and Community provide `zh`, which one
   is used by the keyboard extension?
3. Is Chinese Pinyin activation hard-coded to `zh`, or is there another private
   locale/input-method mapping? Can a code such as `zh_wx` ever opt into Pinyin?
4. Does the Chinese composer read the `.cime` from the selected downloaded
   language pack, or from a distinct Official/bundled location?
5. What is the supported way to evict the previous verified Official `zh`
   assets and force the keyboard extension to reopen newly installed Community
   assets?
6. Can `.clex`, `.cngm`, a neural model, or learned vocabulary suppress or
   reorder an exact `.cime` candidate, even when the installed pack contains no
   model files?
7. Does `pin yin` perform an exact lookup, whitespace normalization, syllable
   lookup plus composition, or a mixture of those paths?

If same-code replacement is not currently supported, documenting that limitation
would prevent Community authors from treating a successful install as an IME
activation. A source selector, a documented override rule, or manifest metadata
for input-method type would make this use case testable.

The intended production data is derived from Rime Wanxiang under CC BY 4.0, but
I have intentionally stopped before publishing a production v3. I will not tune
candidate frequencies until this minimal fingerprint proves which `.cime` is
actually active.
