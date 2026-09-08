#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a standalone Clink Chinese Wanxiang community pack source set.

This v2 deliberately uses a distinct language code (default: zh_wx) so Clink
cannot silently fall back to or collide with the official `zh` pack.

Outputs:
  source/<code>.txt       weighted Clink lexicon source
  source/<code>-ime.tsv   Pinyin -> candidate table (compact + spaced readings)
  Lexicons/<code>.cngm    weighted Chinese next-token model derived from phrases

Then run Clink's official builders:
  python3 build-pack.py <code> source/<code>.txt
  python3 tools/build-ime-table.py <code> source/<code>-ime.tsv
"""
from __future__ import annotations

import argparse
import collections
import math
import re
import struct
import unicodedata
from pathlib import Path

TONE_UMLAUT = str.maketrans({
    'ü':'v','ǖ':'v','ǘ':'v','ǚ':'v','ǜ':'v',
    'Ü':'v','Ǖ':'v','Ǘ':'v','Ǚ':'v','Ǜ':'v',
})
CJK_RANGES = ((0x3400,0x4DBF),(0x4E00,0x9FFF),(0x20000,0x2FA1F))


def is_cjk_char(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)


def cjk_only(text: str) -> bool:
    return bool(text) and all(is_cjk_char(ch) for ch in text)


def normalize_pinyin(raw: str) -> list[str]:
    s = unicodedata.normalize('NFC', raw.strip()).translate(TONE_UMLAUT)
    s = s.replace('u:', 'v').replace('U:', 'v')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    s = unicodedata.normalize('NFC', s).lower()
    s = re.sub(r'[1-5]', '', s)
    parts = re.split(r"[\s'’·\-_/]+", s)
    clean = []
    for part in parts:
        part = re.sub(r'[^a-zv]', '', part)
        if part:
            clean.append(part)
    return clean


def parse_weight(raw: str) -> float:
    raw = raw.strip().rstrip('%')
    try:
        v = float(raw)
    except Exception:
        m = re.search(r'[-+]?\d+(?:\.\d+)?', raw)
        v = float(m.group(0)) if m else 1.0
    return v if math.isfinite(v) and v > 0 else 1.0


def parse_rime(path: Path):
    body = False
    for lineno, raw in enumerate(path.read_text(encoding='utf-8-sig', errors='replace').splitlines(), 1):
        s = raw.strip()
        if not body:
            if s == '...': body = True
            continue
        if not s or s.startswith('#'): continue
        f = raw.split('\t')
        if len(f) < 2: continue
        word = unicodedata.normalize('NFC', f[0].strip())
        reading = f[1].strip()
        weight = parse_weight(f[2]) if len(f) > 2 else 1.0
        if word and reading:
            yield word, reading, weight, lineno


def word_score(word: str, weight: float) -> float:
    # Strongly suppress rare/supplementary single characters without deleting
    # useful rare words entirely. This is specifically meant to stop junk such
    # as 穦 from outranking normal characters such as 拼/品/频.
    score = weight
    if len(word) == 1:
        if ord(word) > 0xFFFF:
            score *= 0.001
        if weight < 5:
            score *= 0.02
        elif weight < 20:
            score *= 0.08
        elif weight < 100:
            score *= 0.25
    return score


def build_cngm(code: str, ordered_words: list[str], freqs: dict[str, float], out: Path, max_following: int = 48):
    ids = {w:i for i,w in enumerate(ordered_words)}
    pair_counts: dict[tuple[str,str], float] = collections.defaultdict(float)

    # Derive high-signal transitions from actual weighted dictionary phrases.
    # 1) character -> character transitions inside words (拼 -> 音)
    # 2) dictionary-word splits inside longer phrases (中文 -> 输入法)
    for phrase, raw_weight in freqs.items():
        if len(phrase) < 2 or len(phrase) > 12 or not cjk_only(phrase):
            continue
        strength = math.sqrt(max(1.0, raw_weight))
        chars = list(phrase)
        for a,b in zip(chars, chars[1:]):
            if a in ids and b in ids:
                pair_counts[(a,b)] += strength

        # All useful two-part dictionary splits, weighted but normalized so long
        # phrases don't flood the model.
        splits = []
        for i in range(1, len(phrase)):
            a,b = phrase[:i], phrase[i:]
            if a in ids and b in ids:
                splits.append((a,b))
        if splits:
            per = strength / max(1.0, math.sqrt(len(splits)))
            for a,b in splits:
                pair_counts[(a,b)] += per

    grouped: dict[str, list[tuple[str,float]]] = collections.defaultdict(list)
    for (a,b), count in pair_counts.items():
        grouped[a].append((b,count))

    ranked = []
    totals = {}
    for prev, items in grouped.items():
        items.sort(key=lambda x: (-x[1], ids[x[0]]))
        kept = items[:max_following]
        totals[prev] = sum(v for _,v in kept)
        for following, count in kept:
            ranked.append(((prev, following), count))
    ranked.sort(key=lambda item: (ids[item[0][0]], -item[1], ids[item[0][1]]))

    blob = bytearray(b'CNGM' + struct.pack('<II', 1, len(ranked)))
    for (prev,_),_count in ranked: blob += struct.pack('<I', ids[prev])
    for (_,following),_count in ranked: blob += struct.pack('<I', ids[following])
    for (prev,_), count in ranked:
        probability = count / totals[prev]
        blob.append(max(0, min(255, round((math.log10(probability) + 6) * 42))))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    print(f'Built {out} with {len(ranked):,} weighted transitions.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+', type=Path)
    ap.add_argument('--code', default='zh_wx')
    ap.add_argument('--out-dir', type=Path, default=Path('source'))
    ap.add_argument('--lexicon-limit', type=int, default=300000)
    ap.add_argument('--max-candidates', type=int, default=16)
    ap.add_argument('--max-ime-readings', type=int, default=300000,
                    help='Global IME reading budget, keeping the highest-signal readings. 0 = unlimited.')
    ap.add_argument('--max-word-length', type=int, default=12)
    ap.add_argument('--max-following', type=int, default=48)
    ap.add_argument('--single-char-ime-min-weight', type=float, default=200.0)
    args = ap.parse_args()

    # word -> best raw frequency
    freqs: dict[str,float] = {}
    # reading -> candidate -> (score, raw weight, first seen)
    readings: dict[str, dict[str, tuple[float,float,int]]] = collections.defaultdict(dict)
    seen = 0

    for path in args.inputs:
        if not path.exists():
            print(f'WARNING: missing input {path}')
            continue
        print(f'Reading {path} ...')
        for word, raw_reading, weight, _lineno in parse_rime(path):
            if not cjk_only(word):
                continue
            if args.max_word_length and len(word) > args.max_word_length:
                continue
            syllables = normalize_pinyin(raw_reading)
            if not syllables:
                continue
            compact = ''.join(syllables)
            spaced = ' '.join(syllables)
            seen += 1
            freqs[word] = max(freqs.get(word, 0.0), weight)
            score = word_score(word, weight)
            # Do not expose ultra-low-frequency single Hanzi as normal Pinyin
            # candidates. They stay in CLEX but cannot pollute the first page.
            if len(word) == 1 and weight < args.single_char_ime_min_weight:
                continue
            for key in ({compact, spaced} if len(syllables) > 1 else {compact}):
                old = readings[key].get(word)
                if old is None or score > old[0]:
                    readings[key][word] = (score, weight, old[2] if old else seen)

    if not freqs:
        raise SystemExit('No usable Wanxiang entries were parsed.')

    # Keep the strongest general vocabulary, then force-include all characters
    # and all top IME candidates so lookup/ranking assets stay consistent.
    ranked_words = sorted(freqs, key=lambda w: (-word_score(w, freqs[w]), -freqs[w], len(w), w))
    keep = set(ranked_words[:args.lexicon_limit] if args.lexicon_limit else ranked_words)
    keep.update(w for w in freqs if len(w) == 1)

    # Bound the IME table so a huge source dictionary cannot make the keyboard
    # load a multi-tens-of-megabytes conversion table. Rank readings by the
    # strongest candidate, while always preserving the regression probes below.
    protected = {
        'pin', 'yin', 'pinyin', 'pin yin',
        'nihao', 'ni hao', 'meiyou', 'mei you',
        'zenmehuishi', 'zen me hui shi',
        'weishenme', 'wei shen me',
        'buzhidao', 'bu zhi dao', 'keyi', 'ke yi',
        'xianzai', 'xian zai', 'jintian', 'jin tian',
        'mingtian', 'ming tian', 'zhongwen', 'zhong wen',
        'shurufa', 'shu ru fa',
    }
    reading_order = sorted(
        readings,
        key=lambda r: (
            -max((meta[0] for meta in readings[r].values()), default=0.0),
            -max((meta[1] for meta in readings[r].values()), default=0.0),
            len(r),
            r,
        ),
    )
    if args.max_ime_readings and len(reading_order) > args.max_ime_readings:
        chosen = set(reading_order[:args.max_ime_readings]) | (protected & set(readings))
        reading_order = [r for r in reading_order if r in chosen]

    ime_rows = {}
    for reading in reading_order:
        candidates = readings[reading]
        ranked = sorted(candidates.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[1][2], kv[0]))
        top = [w for w,_ in ranked[:args.max_candidates]]
        if top:
            ime_rows[reading] = top
            keep.update(top)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    lex_path = args.out_dir / f'{args.code}.txt'
    ime_path = args.out_dir / f'{args.code}-ime.tsv'

    with lex_path.open('w', encoding='utf-8', newline='\n') as f:
        f.write('# word<TAB>frequency — Wanxiang-derived Clink v2\n')
        for word in sorted(keep, key=lambda w: (-freqs.get(w,1.0), w)):
            f.write(f'{word}\t{freqs.get(word,1.0):g}\n')

    with ime_path.open('w', encoding='utf-8', newline='\n') as f:
        f.write('# reading<TAB>candidate... — compact and spaced Pinyin keys\n')
        for reading in sorted(ime_rows):
            f.write('\t'.join([reading, *ime_rows[reading]]) + '\n')

    # CNGM IDs must be the same bytewise order build-pack.py uses.
    ordered = sorted(keep, key=lambda w: w.encode('utf-8'))
    build_cngm(args.code, ordered, freqs, Path('Lexicons')/f'{args.code}.cngm', args.max_following)

    print(f'Lexicon words: {len(keep):,}')
    print(f'IME readings:  {len(ime_rows):,}')
    for probe in ('pin','yin','pinyin','pin yin','nihao','ni hao','meiyou','mei you','zenmehuishi','zen me hui shi'):
        print(probe, '=>', ' / '.join(ime_rows.get(probe, [])[:8]) or 'MISSING')

if __name__ == '__main__':
    main()
