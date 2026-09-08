# Clink Chinese IME black-box plan

The App core source is not present in any public `anti-ltd/clink-*` repository.
These tests therefore change one release variable at a time and treat only the
visible iPhone candidate result as runtime evidence.

| Test | One changed variable | Procedure | Expected observations | Conclusion |
|---|---|---|---|---|
| A. Community pack activation | Repository source: official vs Community; keep code `zh` | Install only the minimal Community `zh` pack and select its source. Type a literal test word and inspect the active language source. | The Community source remains selected and the pack's three-word CLEX is the only downloadable dictionary. | Confirms pack activation, but not CIME use. |
| B. `.cime` activation | Add `zh.cime` to the same minimal Community `zh.clex` | Type `pinyin` and `pin yin`. | `万象验证` is first for both. | Confirms the active candidates came from the Community `.cime`; this is the first release's gate. |
| C. Is `zh` required? | Language code only: publish byte-equivalent two-file packs once as `zh_wx`, once as `zh` | Fully uninstall between runs; use the same rows and no models. | If only `zh` starts Pinyin composition, the code participates in an App-side mapping. If both work, `zh` is not a strict requirement. | Distinguishes language-code dispatch from data quality. It does not identify the private mapping implementation. |
| D. Exact vs segmented lookup | Candidate text only, with direct rows deliberately different from component rows | Use `pin -> 分段甲`, `yin -> 分段乙`, `pinyin -> 连续直查`, and `pin yin -> 空格直查`. Test both inputs. | Direct values prove whole-reading lookup; `分段甲分段乙` proves syllable composition. Different outcomes for the two inputs prove different paths. | Determines lookup behavior without relying on candidate frequency. |
| E. CLEX/CNGM reranking | Model layer only | E1: publish two CIME candidates in fixed order with a deliberately opposite CLEX frequency and no CNGM. E2: keep CIME/CLEX byte-identical and add a matched CNGM that strongly predicts candidate 2 after a fixed preceding token. Keep neural and learning off. | If order changes only in E2 and only with the fixed context, CNGM affects IME ranking. If it never changes, CIME order/composition dominates this case. | Tests model reranking without mismatching CLEX word IDs. A later E3 may add a newly trained matching neural pair. |
| F. Cache invalidation | Release version/hash/candidate only | Install release F1 (`pinyin -> 缓存甲`), publish F2 at a new tag/version/SHA (`pinyin -> 缓存乙`), then compare refresh, uninstall/reinstall, repository removal/re-add, and app restart in that order. | The first operation that changes the visible candidate identifies the effective refresh boundary. Manifest and asset hashes must be recorded for both runs. | Detects stale verified resources and gives a reproducible cache-clearing procedure. |

## Controls for every run

- Use the same Clink version, iPhone, layout, and plain-text test app.
- Type into a fresh empty field; do not accept or teach candidates between runs.
- Disable or reset learned vocabulary when the UI provides that control, and
  record its state.
- Keep neural prediction off until the dedicated model test.
- Capture the active language/source UI, the complete candidate bar, release
  tag, manifest SHA-256, asset SHA-256, and exact keystrokes.
- A successful Action, Release, download, or “Installed” badge is transport
  evidence only. It is never an IME pass.

## Stop/go gate

Do not build or publish Wanxiang v3 until Test B passes on iPhone. If B fails,
continue with C and F before changing any word frequency or adding any corpus.
