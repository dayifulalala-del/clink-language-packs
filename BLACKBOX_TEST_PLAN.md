# Controlled Clink Chinese IME black-box plan

The public resource repositories do not establish the private iOS loader.
A working baseline must be demonstrated before an isolated negative result
can support a conclusion. The old three-word 万象验证 test is retired:
builder acceptance did not prove runtime acceptance of its syllable mismatch.

## Controls and observation record

Keep the same iPhone, exact Clink version/build, Pinyin layout, empty text
context and learning/prediction settings. Record keystrokes (especially Space),
candidate screenshots, selected source, release tag and downloaded checksums.
Do not accept/teach markers. Do not delete user learning merely for a test.
“Installed”, active-source labels, Actions success and download counters are
not candidate-origin proof.

Only the current B probe is published automatically. Do not publish A until
the user has captured B, and do not publish later experiments until their
prerequisite passes. The old v2 versus tiny zh test changed several variables
and is not experiment C.

| Test | One payload variable | Method and positive evidence | Limits / negative result |
|---|---|---|---|
| A. Community CLEX use | CLEX frequency bytes only, fixed word IDs/order | After finding a working dictionary-completion mode, use two existing words for one prefix; invert their frequency bytes between A1/A2. Keep CIME/CNGM absent in both and vocabulary identical. Repeated correlated completion-order changes support Community CLEX participation. | Only proceed if that mode provides completions. No change may mean this mode ignores frequencies; an installed-source label alone is insufficient. This test is not implemented/published yet. |
| B. Community CIME use | Only the pin row in zh.cime | Current B has only 榀; A has only 拼. Keep full CLEX/CNGM byte-identical. Record pin in B → A → B with no Space or acceptance. Correlated marker changes are strong evidence that the Community CIME affects visible candidates. | A single appearance is not exclusive proof: predictions or learning could also provide a character. A negative result leaves dispatch, cache, filtering and compatibility open. |
| C. Code requirement | Code only (plus required filenames/URLs) | After B works as zh, package exactly the same three file bytes as zh_wx. Keep layout and installation state comparable. If both show the marker, zh is not required for this tested configuration. | If only zh works, the code participates in activation or source selection; it does not prove a literal hard-coded equality check. If neither works, inconclusive. |
| D. Space / exact lookup | Only the pin yin row | Starting from working B, retain pin → 榀, pinyin → 拼音 and the existing yin row. Change only pin yin to 品饮 (an existing CLEX word with valid pin yin pronunciation). Compare continuous typing and actual Space keystrokes. If only spaced input changes to 品饮, that distinct reading is consulted. | If both produce 拼音, normalization, segmentation and ranking remain possible. 榀 + a yin character supports syllable participation but does not prove an exact algorithm. If Space commits the prior text, report that event rather than treat it as a literal lookup separator. Test apostrophe/fuzzy input later, one input change at a time. |
| E1. CLEX reranking | Only CLEX frequency bytes | Use a working two-candidate single-syllable CIME row, then invert the candidates' CLEX frequency bytes. Keep vocabulary order/IDs and CNGM byte-identical; no neural model in either run. | Correlated order changes support CLEX influence for this context. No change does not exclude other filtering or multi-syllable effects. |
| E2. CNGM reranking | Only CNGM transition scores | Keep the same CLEX and CIME bytes. Compare matched models with opposite relative scores for two candidates after a fixed preceding word. Do not change word IDs; ensure sorted groups and valid scores. Also test empty context as a control. | Context-specific correlated changes support CNGM influence. No change is inconclusive beyond this input/context. Do not add an old neural model. |
| F1. Version/reload control | Tag/version/URLs only | After B works, republish byte-identical B payload at a new tag. Record UI update state and confirm the marker remains B. | Tests metadata/update behavior without a candidate change; cannot alone detect whether assets were re-downloaded. |
| F2. Cache boundary | Only CIME pin content, with necessary new tag/hash/URL | After the controlled F1, publish A, then observe refresh, language reinstall, repository removal/re-add, app reopening, and finally phone restart **one action at a time**. Capture the candidate after each. Repeat A → B to check reproducibility. | The first correlated change identifies an observed reload boundary, not the private cache implementation. If no action changes it, ask the author for supported diagnostics; do not claim those actions fully cleared private storage. |

## Stage gate

A and B prove different resource layers; B is the immediate task.
Do not train neural models or publish production v3 until Community CIME
participation is supported by controlled iPhone evidence. Current CI verifies
only build and delivery, not tests A–F on a device.

Version, URL and checksum changes accompany a new immutable release. They are
transport variables, not hidden claims of byte-equivalence. F1 separates their
effect before F2 examines a payload transition.
