# Clink Community `zh` IME fingerprint

This release is a deliberately tiny black-box test. It is not the Wanxiang v3
dictionary and it does not replace the v1 or v2 source files in this repository.

## What the release contains

Exactly two files are published for language code `zh`:

- `zh.clex`: a three-entry test lexicon, required for a valid Clink pack.
- `zh.cime`: four Pinyin rows and no production candidate data.

There is no `.cngm`, neural model, emoji metadata, or official fallback asset.
That isolation prevents an old model from obscuring the first loading test.

The table is constructed so that either an exact lookup or syllable composition
has an unmistakable result:

- `pinyin` -> `万象验证`
- `pin yin` -> `万象验证`
- if Clink composes `pin` + `yin`, it gets `万象` + `验证`, also
  `万象验证`

Seeing the pack as installed is not a pass. The test passes only when the iPhone
keyboard shows `万象验证` as the first candidate for both inputs while the
Community Chinese pack is the active language source.

## Evidence boundaries

### Confirmed by public repositories

- The language release manifest has `version` and `packs`; each pack has only a
  `code`, `version`, `assets`, and optional neural metadata. It has no public
  `inputMethod`, locale, profile, or layout field.
- A `.clex` is required. A same-prefix `.cime` is an optional IME table.
- The official builder preserves at most the first 16 candidates in each row.
- Community content is displayed separately from official content by repository
  source.
- Verified downloads are staged, and a failed install leaves the previous pack
  active.
- The official `zh.cime` contains `pin` and `yin` rows but no `pinyin` or
  `pin yin` row. Its first two syllable candidates compose to the observed bad
  candidate `穦因`.

### Inferred from the public data and the reported device result

- Clink can split a multi-syllable reading and combine per-syllable `.cime`
  candidates. That explains why preserving order inside one table row does not
  guarantee the order of dynamically composed candidates.
- `zh_wx` probably lacks the App's built-in Chinese/Pinyin language-to-layout
  mapping and may therefore be treated as a generic language. The core App
  source is not public, so this is not confirmed.

### Requires iPhone black-box testing

- Whether a Community `zh` can become the active Chinese IME instead of the
  official `zh`.
- Same-code source priority, the exact cache key and install directory, and
  whether uninstalling a language removes all previously verified assets.
- Whether `.clex`, `.cngm`, a neural model, or learned vocabulary can reorder IME
  candidates at runtime.

## Clean first test on iPhone

Use Clink 1.4.8 or later; 1.4.8 fixed language deletion.

1. In Clink, remove every installed Chinese entry, including the official one,
   and remove the old `zh_wx` Community entry.
2. Remove `dayifulalala-del/clink-language-packs` from **General ->
   Repositories**.
3. Force-quit both Clink and the app used for typing. Reopen Clink.
4. Add `dayifulalala-del/clink-language-packs` again under **General ->
   Repositories**.
5. In **Languages -> Community**, choose this repository's Chinese (`zh`) entry
   and install it. Do not reinstall official Chinese for this first run.
6. Make the Community Chinese entry the active keyboard language. If Clink asks
   for a layout, choose its built-in Pinyin layout.
7. Open a fresh plain-text field and type `pinyin`, then clear the field and type
   `pin yin`.
8. Record a screenshot of the full candidate bar for each input and note the
   Clink version, whether learning is enabled, and which language/source is shown
   as active.

Pass: `万象验证` is first for both inputs. Fail: official candidates such as
`穦因` remain, raw Latin text is offered, or no IME composition starts.

## Wanxiang attribution

The fingerprint rows above are hand-authored and intentionally do not bundle a
Wanxiang dictionary. The planned production v3 remains derived from
[Rime Wanxiang](https://github.com/amzxyz/rime-wanxiang) by amzxyz and
contributors under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Conversion changes
will include Pinyin normalization, deduplication, frequency-based ranking,
candidate caps, and Clink format generation. The existing detailed attribution
is retained in `WANXIANG_ATTRIBUTION.md` and `WANXIANG_V2.md`.
