#!/usr/bin/env python3
"""Shrink a known-good Wanxiang zh pack so the Clink keyboard can load it.

Why: iOS kills keyboard extensions that use more than a few tens of MB. v3-31-1
shipped 44.9 MB of zh assets: a 650k-reading zh.cime (20 MB of text; a plain
Swift [String: [String]] load of it takes ~80 MB), a 930k-word zh.clex and a
9.9 MB zh.cngm. The official zh pack has ~28k readings and 30k words.

What this does NOT change: candidate order inside every kept row and the CLEX
frequency byte of every kept word. Rows and words are removed, never re-ranked.

CNGM is regenerated, not copied. v3-31-1's zh.cngm was built from a word list
~142 entries longer than zh.clex (build-pack.py drops words such as
"app store"), so every CNGM ID pointed at the wrong CLEX word and 87 pairs
pointed past the end of the dictionary. The new model is built directly on the
final CLEX word IDs with the same pair rules as build_zh_wanxiang_v2.py, using
every phrase of the known-good CLEX as evidence.

How the budget is spent: a row costs far more than a candidate. A Swift
[String: [String]] pays ~64 bytes per row (key handle, array handle, buffer
header) before a single candidate, so a long-tail row holding one candidate
costs five times what that candidate costs. Measured on the v3-31-1 input,
1-2 syllable readings return 28,777 candidates per MB of resident memory
while 6+ syllable readings return only 9,273. The budget therefore buys rows
that serve words people actually type, and it buys them with memory taken back
from the tables that do not decide whether a word can be typed at all.

CIME and CLEX are independent. Clink's own zh pack lists only 61.9% of its CIME
candidates in CLEX, and only 63.4% of its first candidates, so a candidate is
offered without a CLEX entry of its own. CLEX carries frequency help and the
CNGM word IDs at ~50 bytes of resident memory per word, so --max-clex-words
caps it near the official pack's size and the freed memory pays for CIME rows:
at 150k readings that moves CLEX from 7.4 MB to 2.0 MB and CNGM from 6.0 MB to
3.0 MB, and the 8.4 MB buys 94,585 more readings. Measured against the full
v3-31-1 table, words ranked 50k-150k go from 6.6% to 84.6% reachable while the
top 50,000 stay at 99.8% / 99.4% / 99.0%.

--candidate-tiers truncates deeper on longer readings, which the candidate bar
cannot show anyway. --target-rank is the opposite lever, for shrinking rather
than growing: it keeps a Chinese row only when one of its candidates is among
the N most frequent known-good words, so a small --max-readings spends its
budget on common words first.

What it removes:
  * readings the official zh table never uses: anything outside a-z, i.e.
    syllable-spaced duplicates ("pin yin" next to "pinyin") and digit keys that
    a Pinyin composition cannot contain, plus readings longer than --max-key.
  * Chinese rows that cannot produce any word inside --target-rank, then
    long-tail readings whose best candidate has the lowest CLEX frequency.
    Chinese and Latin rows have separate budgets because Wanxiang weights
    English far below Chinese.
  * English typo aliases ("githbu" -> GitHub), unless --keep-latin-typos.
  * candidates past the --candidate-tiers cap for the reading's length, except
    where a word inside --target-rank sits deeper (then the row keeps up to
    --max-candidates). Single syllables keep all 16.
  * CLEX words no kept reading can produce.

Always kept: every single-syllable row, every project shortcut / domain /
Latin term from source/, every Chinese correction from the Rime dictionaries
passed with --corrections (Wanxiang's cuoyin.dict.yaml: wrong readings and
characters such as "maopeifang" -> 毛坯房), the project misreadings in
source/zh-cuoyin-extra.tsv, and the regression readings below.

What it adds: Pinyin slip rows for single syllables and the most frequent
words, e.g. "zhognguo" -> 中国, "nihoa" -> 你好. Only the systematic slips that
Sogou and libpinyin correct are generated, and a slip is dropped when it is
itself valid Pinyin or an existing reading, so normal input is never shadowed.

Usage:
  python3 tools/compact_zh_pack.py --cime known/zh.cime --clex known/zh.clex
Writes Lexicons/zh.cime, Lexicons/zh.clex and Lexicons/zh.cngm.
"""
import argparse
import collections
import json
import math
import re
import struct
import unicodedata
from functools import lru_cache
from pathlib import Path

REGRESSION_EXACT = {
    'pinyin': '拼音', 'nihao': '你好', 'dihao': '帝豪', 'jilidihao': '吉利帝豪',
    'kjzl': '快捷指令', 'smj': '什么价', 'smjia': '什么价', 'qujianma': '取件码',
    'xunihao': '虚拟号', 'github': 'GitHub', 'appstore': 'App Store',
    'computer': 'computer', 'maopeifang': '毛坯房',
    'heilongjiang': '黑龙江', 'ruanluyou': '软路由', 'weishenme': '为什么',
    'buzhidao': '不知道', 'chatgpt': 'ChatGPT', 'python': 'Python',
}
REGRESSION_CONTAINS = {'bzd': '不知道', 'wsm': '为什么', 'zmhs': '怎么回事', 'yyds': 'YYDS'}
TONELESS = str.maketrans({ch: base for base, marks in {
    'a': 'āáǎà', 'e': 'ēéěè', 'i': 'īíǐì', 'o': 'ōóǒò', 'u': 'ūúǔù', 'v': 'ǖǘǚǜü'}.items() for ch in marks})
# Systematic Pinyin slips corrected by Sogou (ign/img/uei/uen/iou) and
# libpinyin (gn, on, ue/v), plus the ao and ia/ua transpositions.
PINYIN_TYPOS = [
    (re.compile(r'ng$'), 'gn'),                   # dign -> ding, zhogn -> zhong
    (re.compile(r'ing$'), 'img'),                 # dimg -> ding
    (re.compile(r'ong$'), 'on'),                  # zhonguo -> zhongguo
    (re.compile(r'ui$'), 'uei'),                  # guei -> gui
    (re.compile(r'^([^jqxy]+)un$'), r'\1uen'),    # luen -> lun
    (re.compile(r'iu$'), 'iou'),                  # liou -> liu
    (re.compile(r'ao$'), 'oa'),                   # nihoa -> nihao
    (re.compile(r'([iu])a(o|n|ng)$'), r'a\1\2'),  # tain -> tian, xaio -> xiao
    (re.compile(r'^([jqxy])u'), r'\1v'),          # jv -> ju
]
UMLAUT = re.compile(r'^([nl])ve$')                # lue -> lve (略), although lu+e also parses
REGRESSION_TYPOS = {'zhognguo': '中国', 'nihoa': '你好', 'jintain': '今天', 'shagnhai': '上海', 'lue': '略'}
HAN = re.compile(r'^[\u3400-\u9fff\U00020000-\U0003134f]$')


def norm(text: str) -> str:
    return unicodedata.normalize('NFC', text).lower()


def read_clex(path: Path):
    data = path.read_bytes()
    if data[:4] != b'CLEX' or struct.unpack_from('<I', data, 4)[0] != 1:
        raise SystemExit(f'{path} is not CLEX v1')
    count, size = struct.unpack_from('<II', data, 8)
    matrix_start = 16 + 4 * size
    offsets_start = matrix_start + (size + 1) * size
    offsets = struct.unpack_from(f'<{count + 1}I', data, offsets_start)
    probs_start = offsets_start + 4 * (count + 1)
    blob = probs_start + 2 * count
    words = [data[blob + offsets[i]:blob + offsets[i + 1]].decode('utf-8') for i in range(count)]
    return {
        'words': words,
        'probs': data[probs_start:probs_start + count],
        'lengths': data[probs_start + count:blob],
        # Alphabet and letter-transition matrix are corpus statistics; reusing
        # them verbatim keeps Clink's spelling help identical to the known-good pack.
        'header_tail': data[16:offsets_start],
        'alphabet_size': size,
    }


def write_clex(path: Path, clex, keep_ids):
    kept = [clex['words'][i] for i in keep_ids]
    out = bytearray(b'CLEX' + struct.pack('<III', 1, len(kept), clex['alphabet_size']))
    out += clex['header_tail']
    offset = 0
    for word in kept:
        out += struct.pack('<I', offset)
        offset += len(word.encode('utf-8'))
    out += struct.pack('<I', offset)
    out += bytes(clex['probs'][i] for i in keep_ids)
    out += bytes(clex['lengths'][i] for i in keep_ids)
    for word in kept:
        out += word.encode('utf-8')
    path.write_bytes(out)


def is_cjk(text: str) -> bool:
    return bool(text) and all(HAN.match(ch) for ch in text)


def build_cngm(path: Path, lexicon: list[str], phrases, max_following: int) -> int:
    """Next-word pairs over `lexicon` IDs, mirroring build_zh_wanxiang_v2.build_cngm."""
    ids = {w: i for i, w in enumerate(lexicon)}
    pairs = collections.defaultdict(float)
    for phrase, weight in phrases:
        if len(phrase) < 2 or len(phrase) > 16 or not is_cjk(phrase):
            continue
        strength = math.sqrt(max(1.0, weight))
        for a, b in zip(phrase, phrase[1:]):
            if a in ids and b in ids:
                pairs[(a, b)] += strength
        splits = [(phrase[:i], phrase[i:]) for i in range(1, len(phrase))
                  if phrase[:i] in ids and phrase[i:] in ids]
        for a, b in splits:
            pairs[(a, b)] += strength / max(1.0, math.sqrt(len(splits)))

    grouped = collections.defaultdict(list)
    for (a, b), count in pairs.items():
        grouped[a].append((b, count))
    ranked = []
    for a, items in grouped.items():
        items.sort(key=lambda x: (-x[1], ids[x[0]]))
        kept = items[:max_following]
        total = sum(c for _, c in kept)
        ranked += [(ids[a], ids[b], c / total, c) for b, c in kept]
    # Groups ascend by previous ID, most frequent first (tools/build-next-word.py).
    ranked.sort(key=lambda r: (r[0], -r[3], r[1]))
    blob = bytearray(b'CNGM' + struct.pack('<II', 1, len(ranked)))
    blob += struct.pack(f'<{len(ranked)}I', *(r[0] for r in ranked))
    blob += struct.pack(f'<{len(ranked)}I', *(r[1] for r in ranked))
    blob += bytes(max(0, min(255, round((math.log10(r[2]) + 6) * 42))) for r in ranked)
    path.write_bytes(blob)
    return len(ranked)


def read_cime(path: Path):
    rows = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        fields = line.split('\t')
        if len(fields) >= 2:
            rows[fields[0]] = fields[1:]
    return rows


def read_rime_dict(path: Path):
    """(word, compact reading) pairs from a Rime *.dict.yaml body."""
    body = False
    for line in path.read_text(encoding='utf-8').splitlines():
        if line == '...':
            body = True
            continue
        fields = line.split('\t')
        if body and len(fields) >= 2 and not line.startswith('#'):
            reading = fields[1].lower().replace('u:', 'v').translate(TONELESS)
            yield fields[0], re.sub(r'[^a-z]', '', reading)


def read_extra_corrections(path: Path):
    """(word, misread reading) pairs maintained in source/zh-cuoyin-extra.tsv."""
    if not path.exists():
        return []
    pairs = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        fields = raw.split('\t')
        if raw.strip() and not raw.startswith('#') and len(fields) >= 2:
            pairs.append((fields[0].strip(), fields[1].strip().lower()))
    return pairs


def pinyin_typos(kept, syllables, sources, max_key, max_candidates=5):
    """Rows keyed by common slips of each source reading, merged in source order."""
    safe = syllables - {'n', 'ng'}  # 嗯 never sits inside a typed word

    @lru_cache(maxsize=None)
    def splits(text):
        if not text:
            return ((),)
        return tuple((text[:j],) + rest for j in range(1, min(6, len(text)) + 1)
                     if text[:j] in syllables for rest in splits(text[j:]))

    @lru_cache(maxsize=None)
    def parses(text):
        return not text or any(text[:j] in safe and parses(text[j:]) for j in range(1, min(6, len(text)) + 1))

    merged = collections.defaultdict(list)
    for rank, reading in enumerate(sources):
        parts = next((p for p in splits(reading) if len(p) == len(kept[reading][0])), None)
        for i, part in enumerate(parts or ()):
            slips = [(pattern.sub(replacement, part), True) for pattern, replacement in PINYIN_TYPOS
                     if pattern.search(part)]
            if UMLAUT.search(part):
                slips.append((UMLAUT.sub(r'\1ue', part), False))
            for slip, strict in slips:
                key = ''.join(parts[:i] + (slip,) + parts[i + 1:])
                # A strict slip must not shadow a reading that already exists. The
                # umlaut slip may: "lue" is how people type "lüe" (略), and the
                # lu+e split it also parses as (卤鹅) is far rarer. Both are kept,
                # the umlaut word first, by the merge where rows are written.
                if len(key) > max_key or (strict and (key in kept or parses(key))):
                    continue
                merged[key].append(rank)
    rows = {}
    for key, ranks in merged.items():
        candidates = []
        for rank in sorted(set(ranks)):
            candidates += [c for c in kept[sources[rank]] if c not in candidates]
        rows[key] = candidates[:max_candidates]
    return rows


def edit_distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def protected_terms(source: Path):
    """Terms and readings the project maintains by hand."""
    terms, readings = set(), set()
    shortcuts = source / 'zh-shortcuts.tsv'
    domain = source / 'zh-domain-terms.tsv'
    latin = source / 'zh-latin-terms.tsv'
    for path in (shortcuts, domain):
        if not path.exists():
            continue
        for raw in path.read_text(encoding='utf-8').splitlines():
            if not raw.strip() or raw.lstrip().startswith('#'):
                continue
            fields = raw.split('\t')
            terms.add(fields[0].strip())
            if len(fields) > 1 and fields[1].strip():
                reading = fields[1].strip().lower()
                readings.add(reading.replace(' ', ''))
    if latin.exists():
        for raw in latin.read_text(encoding='utf-8').splitlines():
            if not raw.strip() or raw.lstrip().startswith('#'):
                continue
            fields = raw.split('\t')
            terms.add(fields[0].strip())
            if len(fields) > 2:
                readings.update(a.strip().lower() for a in fields[2].split(',') if a.strip())
    return terms, readings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cime', type=Path, required=True)
    ap.add_argument('--clex', type=Path, required=True)
    ap.add_argument('--code', default='zh')
    ap.add_argument('--source', type=Path, default=Path('source'))
    ap.add_argument('--out-dir', type=Path, default=Path('Lexicons'))
    ap.add_argument('--max-readings', type=int, default=150000, help='Chinese readings kept')
    ap.add_argument('--max-latin', type=int, default=12000, help='English / brand readings kept')
    ap.add_argument('--target-rank', type=int, default=0,
                    help='keep a Chinese row only when it can produce one of the N most '
                         'frequent known-good words; 0 keeps every row the budget allows')
    ap.add_argument('--corrections', type=Path, nargs='*', default=[],
                    help='Rime dictionaries whose readings are Chinese corrections to keep in full')
    ap.add_argument('--keep-latin-typos', action='store_true',
                    help='keep English typo aliases such as "githbu" -> GitHub')
    ap.add_argument('--pinyin-typo-words', type=int, default=20000,
                    help='most frequent words that also get Pinyin slip rows (0 disables slips)')
    ap.add_argument('--max-clex-words', type=int, default=40000,
                    help='cap CLEX at the N most frequent words a kept row can produce; '
                         '0 keeps every one of them')
    ap.add_argument('--max-key', type=int, default=24, help='longest reading kept')
    ap.add_argument('--candidate-tiers', default='6:6,10:4,24:3',
                    help='per-reading-length candidate caps as len:cap pairs; longer '
                         'readings are more precise and need fewer candidates')
    ap.add_argument('--max-candidates', type=int, default=10,
                    help='candidates kept on multi-syllable rows')
    ap.add_argument('--max-following', type=int, default=4,
                    help='next-word pairs kept per previous word (0 drops CNGM)')
    ap.add_argument('--receipt', type=Path)
    args = ap.parse_args()

    source_rows = read_cime(args.cime)
    typeable = re.compile(rf'^[a-z]{{1,{args.max_key}}}$')
    rows = {r: v for r, v in source_rows.items() if typeable.match(r)}
    clex = read_clex(args.clex)
    words = clex['words']
    word_id = {w: i for i, w in enumerate(words)}
    prob = clex['probs']

    def score(cands):
        return max((prob[word_id[norm(c)]] for c in cands if norm(c) in word_id), default=0)

    syllables = {r for r, v in rows.items()
                 if r.isascii() and r.isalpha() and len(r) <= 6 and HAN.match(v[0])}

    # Frequency rank of every Chinese word in the known-good CLEX. Rows are kept
    # for the words they can actually produce, not for their own best score.
    zh_rank = {}
    if args.target_rank > 0:
        ranked = sorted((i for i, w in enumerate(words) if is_cjk(w)),
                        key=lambda i: (-prob[i], words[i].encode()))
        zh_rank = {words[i]: n for n, i in enumerate(ranked)}

    def top_positions(cands):
        """Indexes of candidates that are among the --target-rank most frequent words."""
        return [i for i, c in enumerate(cands) if zh_rank.get(norm(c), 1 << 30) < args.target_rank]

    tiers = sorted(tuple(int(n) for n in part.split(':')) for part in args.candidate_tiers.split(','))

    def tier_cap(reading):
        return next((cap for limit, cap in tiers if len(reading) <= limit), tiers[-1][1])

    def latin(r):
        return rows[r][0].isascii()

    def latin_typo(r):
        # "githbu" -> GitHub, but not "ljiu" -> L9 or "dotnet" -> .NET.
        spellings = [re.sub(r'[^a-z0-9]', '', c.lower()) for c in rows[r]]
        return latin(r) and r not in spellings and min(edit_distance(r, w) for w in spellings) <= 2

    typeable_count = len(rows)
    dropped = set() if args.keep_latin_typos else {r for r in rows if latin_typo(r)}
    rows = {r: v for r, v in rows.items() if r not in dropped}

    # Project misreadings: the right word goes fifth on the misread row, so it
    # stays on the first page without displacing the row's own top four.
    corrections = {}
    extra = read_extra_corrections(args.source / 'zh-cuoyin-extra.tsv')
    for word, reading in extra:
        if typeable.match(reading):
            row = rows.setdefault(reading, [])
            if word not in row:
                row.insert(min(len(row), 4), word)
                del row[16:]
            corrections[reading] = max(corrections.get(reading, 0), row.index(word) + 1)

    # Chinese corrections: the correcting word must survive candidate truncation.
    for path in args.corrections:
        for word, reading in read_rime_dict(path):
            if word in rows.get(reading, []):
                corrections[reading] = max(corrections.get(reading, 0), rows[reading].index(word) + 1)

    terms, manual_readings = protected_terms(args.source)
    protected = set(syllables) | set(corrections)
    protected.update(r for r in manual_readings if r in rows)
    protected.update(r for r in REGRESSION_EXACT if r in rows)
    protected.update(r for r in REGRESSION_CONTAINS if r in rows)
    for r, v in rows.items():
        if any(c in terms for c in v[:3]):
            protected.add(r)

    chinese = sorted((r for r in rows if r not in protected and not latin(r)
                      and (not zh_rank or top_positions(rows[r]))),
                     key=lambda r: (-score(rows[r]), len(r), r))
    english = sorted((r for r in rows if r not in protected and latin(r)),
                     key=lambda r: (-score(rows[r]), len(r), r))
    chinese_budget = max(0, args.max_readings - sum(1 for r in protected if not latin(r)))
    latin_budget = max(0, args.max_latin - sum(1 for r in protected if latin(r)))
    selected = protected | set(chinese[:chinese_budget]) | set(english[:latin_budget])
    def truncate(r):
        if r in syllables:
            return rows[r]                       # 401 single-syllable rows: single characters keep all 16
        depth = tier_cap(r)
        hit = top_positions(rows[r])
        if hit:                                  # never cut off the frequent word this row was kept for
            depth = max(depth, min(hit[-1] + 1, args.max_candidates))
        return rows[r][:max(depth, corrections.get(r, 0))]

    kept = {r: truncate(r) for r in selected}

    typos = {}
    if args.pinyin_typo_words > 0:
        words_first = sorted((r for r in kept if r not in syllables and is_cjk(kept[r][0])),
                             key=lambda r: (-score(kept[r]), len(r), r))
        umlaut = [r for r in words_first[args.pinyin_typo_words:] if 'lve' in r or 'nve' in r]
        sources = sorted(syllables & set(kept), key=lambda r: (-score(kept[r]), r))
        typos = pinyin_typos(kept, syllables, sources + words_first[:args.pinyin_typo_words] + umlaut,
                             args.max_key)

    # Kept rows are the known-good rows truncated, never reordered.
    args.out_dir.mkdir(parents=True, exist_ok=True)
    cime_path = args.out_dir / f'{args.code}.cime'
    def row(r):
        if r in kept and r in typos:      # umlaut slip landing on a real reading
            merged_row = list(typos[r]) + [c for c in kept[r] if c not in typos[r]]
            return merged_row[:max(args.max_candidates, corrections.get(r, 0))]
        return kept.get(r, typos.get(r))

    with cime_path.open('w', encoding='utf-8', newline='\n') as out:
        for r in sorted({**kept, **typos}):
            out.write('\t'.join([r, *row(r)]) + '\n')

    kept_ids = {word_id[norm(c)] for r in {**kept, **typos} for c in row(r) if norm(c) in word_id}
    if 0 < args.max_clex_words < len(kept_ids):
        # CIME and CLEX are independent tables. Clink's own zh pack lists only
        # 61.9% of its CIME candidates in CLEX (63.4% of the first candidates),
        # so a candidate needs no CLEX entry to be offered. CLEX carries the
        # frequency help and the CNGM word IDs, and costs ~50 bytes of resident
        # memory per word, so cap it at the frequent words plus what the project
        # protects and spend the rest of the budget on CIME rows instead.
        must = {word_id[norm(c)] for r in protected if r in kept
                for c in row(r) if norm(c) in word_id}
        must |= {word_id[norm(w)] for w in terms if norm(w) in word_id}
        must |= {word_id[norm(w)] for w in
                 (*REGRESSION_EXACT.values(), *REGRESSION_CONTAINS.values(), *REGRESSION_TYPOS.values())
                 if norm(w) in word_id}
        must &= kept_ids
        rest = sorted(kept_ids - must, key=lambda i: (-prob[i], words[i].encode()))
        kept_ids = must | set(rest[:max(0, args.max_clex_words - len(must))])
    keep_word_ids = sorted(kept_ids)
    write_clex(args.out_dir / f'{args.code}.clex', clex, keep_word_ids)

    cngm_path = args.out_dir / f'{args.code}.cngm'
    cngm_pairs = 0
    if args.max_following > 0:
        # CLEX bytes are round((log10(p) + 9) * 28); undo that for pair weights.
        phrases = ((w, 10 ** (b / 28)) for w, b in zip(words, prob))
        cngm_pairs = build_cngm(cngm_path, [words[i] for i in keep_word_ids], phrases, args.max_following)
    elif cngm_path.exists():
        cngm_path.unlink()

    # Regression gate: everything the known-good pack answered must still answer.
    out_rows = read_cime(cime_path)
    failed = []
    for key, want in REGRESSION_EXACT.items():
        if key in rows and rows[key][0] == want and out_rows.get(key, [None])[0] != want:
            failed.append((key, want, out_rows.get(key, [])[:5]))
    for key, want in REGRESSION_CONTAINS.items():
        if key in rows and want in rows[key][:8] and want not in out_rows.get(key, [])[:8]:
            failed.append((key, want, out_rows.get(key, [])[:8]))
    for r in protected:
        if out_rows.get(r) != kept[r] or kept[r] != rows[r][:len(kept[r])]:
            failed.append(('protected row changed', r))
    for r, depth in corrections.items():
        if out_rows.get(r, [])[:depth] != rows[r][:depth]:
            failed.append(('correction lost', r))
    for word, reading in extra:
        if typeable.match(reading) and word not in out_rows.get(reading, []):
            failed.append(('extra correction lost', reading, word))
    if args.pinyin_typo_words > 0:
        for key, want in REGRESSION_TYPOS.items():
            if out_rows.get(key, [None])[0] != want:
                failed.append(('pinyin slip', key, want, out_rows.get(key, [])[:3]))
    if any(not typeable.match(r) for r in out_rows):
        failed.append('non a-z reading written')
    if failed:
        raise SystemExit('Compact regression failure: ' + repr(failed[:20]))

    receipt = {
        'profile': 'compact',
        'maxReadings': args.max_readings,
        'maxLatin': args.max_latin,
        'maxKey': args.max_key,
        'targetRank': args.target_rank,
        'candidateTiers': args.candidate_tiers,
        'maxClexWords': args.max_clex_words,
        'maxCandidates': args.max_candidates,
        'maxFollowing': args.max_following,
        'keepLatinTypos': args.keep_latin_typos,
        'pinyinTypoWords': args.pinyin_typo_words,
        'input': {'readings': len(source_rows), 'clexWords': len(words)},
        'output': {
            'readings': len(out_rows),
            'candidates': sum(len(v) for v in out_rows.values()),
            'protectedReadings': len(protected),
            'chineseCorrectionReadings': len(corrections),
            'extraCorrections': len(extra),
            'pinyinTypoReadings': len(typos),
            'droppedLatinTypoReadings': len(dropped),
            'droppedNonTypeableReadings': len(source_rows) - typeable_count,
            'clexWords': len(keep_word_ids),
            'cngmPairs': cngm_pairs,
            'bytes': {p.name: p.stat().st_size for p in (cime_path, args.out_dir / f'{args.code}.clex', cngm_path) if p.exists()},
        },
    }
    if args.receipt:
        args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
