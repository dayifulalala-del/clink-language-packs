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

What it removes:
  * readings the official zh table never uses: anything outside a-z, i.e.
    syllable-spaced duplicates ("pin yin" next to "pinyin") and digit keys that
    a Pinyin composition cannot contain, plus readings longer than --max-key.
  * long-tail readings whose best candidate has the lowest CLEX frequency.
    Chinese and Latin rows have separate budgets because Wanxiang weights
    English far below Chinese; every exact English word is ranked before
    generated typo aliases.
  * candidates past --max-candidates on multi-syllable rows (single syllables
    keep all 16).
  * CLEX words no kept reading can produce.

Always kept: every single-syllable row, every project shortcut / domain /
Latin term from source/, and the regression readings below.

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
from pathlib import Path

REGRESSION_EXACT = {
    'pinyin': '拼音', 'nihao': '你好', 'dihao': '帝豪', 'jilidihao': '吉利帝豪',
    'kjzl': '快捷指令', 'smj': '什么价', 'smjia': '什么价', 'qujianma': '取件码',
    'xunihao': '虚拟号', 'github': 'GitHub', 'appsrore': 'App Store',
    'computer': 'computer', 'compuer': 'computer', 'maopeifang': '毛坯房',
    'heilongjiang': '黑龙江', 'ruanluyou': '软路由', 'weishenme': '为什么',
    'buzhidao': '不知道', 'chatgpt': 'ChatGPT', 'python': 'Python',
}
REGRESSION_CONTAINS = {'bzd': '不知道', 'wsm': '为什么', 'zmhs': '怎么回事', 'yyds': 'YYDS'}
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
    ap.add_argument('--max-readings', type=int, default=80000, help='Chinese readings kept')
    ap.add_argument('--max-latin', type=int, default=30000,
                    help='English / brand readings kept (exact words before typo aliases)')
    ap.add_argument('--max-key', type=int, default=24, help='longest reading kept')
    ap.add_argument('--max-candidates', type=int, default=10,
                    help='candidates kept on multi-syllable rows')
    ap.add_argument('--max-following', type=int, default=10,
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

    terms, manual_readings = protected_terms(args.source)
    protected = set(syllables)
    protected.update(r for r in manual_readings if r in rows)
    protected.update(r for r in REGRESSION_EXACT if r in rows)
    protected.update(r for r in REGRESSION_CONTAINS if r in rows)
    for r, v in rows.items():
        if any(c in terms for c in v[:3]):
            protected.add(r)

    def latin(r):
        return rows[r][0].isascii()

    def exact_word(r):
        return any(re.sub(r'[^a-z0-9]', '', c.lower()) == r for c in rows[r])

    chinese = sorted((r for r in rows if r not in protected and not latin(r)),
                     key=lambda r: (-score(rows[r]), len(r), r))
    english = sorted((r for r in rows if r not in protected and latin(r)),
                     key=lambda r: (not exact_word(r), -score(rows[r]), len(r), r))
    chinese_budget = max(0, args.max_readings - sum(1 for r in protected if not latin(r)))
    latin_budget = max(0, args.max_latin - sum(1 for r in protected if latin(r)))
    selected = protected | set(chinese[:chinese_budget]) | set(english[:latin_budget])
    kept = {r: rows[r] if r in syllables else rows[r][:args.max_candidates] for r in selected}

    # Kept rows are the known-good rows truncated, never reordered.
    args.out_dir.mkdir(parents=True, exist_ok=True)
    cime_path = args.out_dir / f'{args.code}.cime'
    with cime_path.open('w', encoding='utf-8', newline='\n') as out:
        for r in sorted(kept):
            out.write('\t'.join([r, *kept[r]]) + '\n')

    keep_word_ids = sorted({word_id[norm(c)] for v in kept.values() for c in v if norm(c) in word_id})
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
    if any(not typeable.match(r) for r in out_rows):
        failed.append('non a-z reading written')
    if failed:
        raise SystemExit('Compact regression failure: ' + repr(failed[:20]))

    receipt = {
        'profile': 'compact',
        'maxReadings': args.max_readings,
        'maxLatin': args.max_latin,
        'maxKey': args.max_key,
        'maxCandidates': args.max_candidates,
        'maxFollowing': args.max_following,
        'input': {'readings': len(source_rows), 'clexWords': len(words)},
        'output': {
            'readings': len(out_rows),
            'candidates': sum(len(v) for v in out_rows.values()),
            'protectedReadings': len(protected),
            'droppedNonTypeableReadings': len(source_rows) - len(rows),
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
