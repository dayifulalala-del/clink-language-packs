# How can we verify which Community Chinese CIME is active?

Thanks for improving the official Chinese implementation. I am testing the
latest App version available to me, but will attach the exact version/build
and candidate screenshots rather than rely on the word “latest”.

I would like to contribute usable Wanxiang-derived Chinese data. Before
reporting an App bug, we audited our own fork and found problems in our earlier
experiment. This note **supersedes the claims in commit 4cc48bb**.

## Corrections to our earlier report

- The old three-word fingerprint mapped one Pinyin syllable to two Hanzi and
  two syllables to four Hanzi. The public builder accepts those rows, but we
  have not established that the runtime composer accepts them.
- The old test changed CLEX coverage, CIME and model presence together.
  A negative result was not a controlled source-selection test.
- Historical zh_wx v2 and the tiny zh fingerprint were NOT byte-equivalent.
- We do not have recorded proof that every proposed cleanup step was performed
  or that a specific release was active on the phone.
- We found different release-discovery endpoints returning different tags:
  releases/latest returned the tiny zh fingerprint, while the first item of
  releases?per_page=1 returned zh_wx v2. Which endpoint the App uses is unknown.
- Our own verification downloads increment asset download counts; those counts
  do not identify iPhone downloads.
- Therefore we cannot conclude that Community zh replacement is unsupported,
  or that the keyboard definitely read Official assets.

The earlier reported pin yin results (穦因, 拼因, etc.) resemble combinations
of the inspected official pin/yin rows. That is a useful clue, not proof of
the active file or of a particular segmentation algorithm.

## New controlled test

[Current test instructions](FINGERPRINT_TEST.md) and
[full black-box plan](BLACKBOX_TEST_PLAN.md).

Both variants use code zh and the same complete Wanxiang-derived CLEX/CNGM
pair. The only payload difference is one CIME reading:

- A: pin has the single candidate 拼.
- B: pin has the single candidate 榀.

Both markers have a matching Pinyin pronunciation and already exist in the
unchanged CLEX. Every other CIME row is byte-identical, including pinyin and
pin yin (first candidate 拼音). No official neural model is bundled.
The release contains only the three zh resources and manifest.json.

The workflow verifies pinned baseline hashes, binary integrity, the matched
model pair and all asset URLs/hashes/sizes. It explicitly sets Latest, checks
the first release-list entry as well, then downloads and verifies the published
files. Version/tag changes are necessary transport metadata; they do not
change CLEX/CNGM content or unrelated CIME rows.

**Device result: pending.** We will record B, then A, then B under the same
layout, learning state and empty context. Installation status is not a pass.
Please do not treat this document as an already-reproduced App defect.

## Questions that require App-side knowledge

1. Is selecting a Community pack with code zh intended to replace the Chinese
   IME resources of Official zh? What UI selects that source?
2. Are installed resources keyed by code or by (repository, code)? What happens
   when both sources provide zh?
3. Does Pinyin dispatch require zh, or can an additional code opt in? Is there
   metadata beyond the public release generator's code/version/assets fields?
4. Does the composer use exact CIME readings, normalized readings, syllable
   composition, or a mixture? Can runtime constraints reject otherwise valid
   builder output?
5. At what stage can CLEX frequencies, CNGM, neural prediction or learning
   filter/reorder CIME candidates?
6. Which release-discovery endpoint does the App use? What operation forces a
   new manifest/asset download and keyboard-extension resource reload?
7. Could the App expose the active repository, pack version and CIME checksum
   in diagnostics? This would make contributions much easier to verify.

We found public resource tooling and documentation, but no public iOS core
implementation. We are asking about the supported contract rather than
asserting private loading behavior. The planned production data is derived
from Rime Wanxiang by amzxyz and contributors under CC BY 4.0; production v3
remains gated on device evidence.
