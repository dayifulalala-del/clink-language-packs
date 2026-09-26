#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Clink Chinese Wanxiang sources.

Historical v2 used this file for zh_wx. The production v3 wrapper now reuses
the same converter with code=zh and enables extra mixed-input features.

LITE ADAPTATION (build_zh_wanxiang_v2_lite.py): same converter, adjusted for
Wanxiang's lite-dicts.zip (*.lite.dict.yaml, toneless):
  * source_name() strips the ".lite" infix so SPECIAL_SOURCES /
    TOLERANCE_SOURCES and the jichu core-compact budget keep working;
  * strip_marks() maps syllabic nasals ḿ/m̀ -> "me", ň/ǹ/ń -> "en", matching
    Wanxiang release-build.sh's tone_map (the generic strip would give "m"/"n");
  * SPECIAL_SOURCES extended with lite's domain tables (shici, renming,
    yixue, huaxue, yaopin, wuzhong);
  * rows whose code column still contains CJK (upstream placeholder for a
    rare character with no pinyin) are skipped.

Outputs:
  source/<code>.txt       weighted Clink lexicon source
  source/<code>-ime.tsv   reading -> ordered candidates
  Lexicons/<code>.cngm    weighted next-token model coupled to the CLEX word IDs
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
# CHANGE (lite): Wanxiang's release-build.sh tone_map sends the syllabic
# nasals to a vowel form, not a bare consonant: ḿ/m̀ -> "me", ň/ǹ/ń -> "en".
# Handled in strip_marks() below so toned overlays produce the same keys.
CJK_RANGES = ((0x3400,0x4DBF),(0x4E00,0x9FFF),(0x20000,0x2FA1F))
SPECIAL_SOURCES = {'diming', 'mingren', 'yiren', 'taifeng', 'fangyan',
                   # CHANGE (lite): lite pack's extra domain tables get the
                   # same protected reading budget as the original specials.
                   'shici', 'renming', 'yixue', 'huaxue', 'yaopin', 'wuzhong'}
TOLERANCE_SOURCES = {'cuoyin', 'duoyin'}
# CHANGE (lite): upstream leaves a CJK placeholder when a rare character has
# no pinyin (e.g. code "duan xu 𱇮"); such rows get a truncated, wrong reading.
CJK_IN_CODE = re.compile(r'[\u3400-\u9fff\U00020000-\U0002fa1f]')


def is_cjk_char(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)


def cjk_only(text: str) -> bool:
    return bool(text) and all(is_cjk_char(ch) for ch in text)


def strip_marks(raw: str) -> str:
    s = unicodedata.normalize('NFC', raw.strip()).translate(TONE_UMLAUT)
    s = s.replace('u:', 'v').replace('U:', 'v')
    s = unicodedata.normalize('NFD', s)
    # CHANGE (lite): syllabic-nasal parity with Wanxiang's tone_map
    # (ḿ/m̀ -> "me", ň/ǹ/ń -> "en"); the generic Mn strip below would
    # otherwise leave "m"/"n", which never matches lite's keys.
    # U+0300 grave, U+0301 acute, U+0304 macron, U+030C caron (NFD form).
    s = re.sub(r'm[\u0300\u0301\u0304]', 'me', s)
    s = re.sub(r'n[\u0300\u0301\u030c]', 'en', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return unicodedata.normalize('NFC', s).lower()


def normalize_pinyin(raw: str) -> list[str]:
    s = re.sub(r'[1-5]', '', strip_marks(raw))
    parts = re.split(r"[\s'’·\-_/]+", s)
    clean = []
    for part in parts:
        part = re.sub(r'[^a-zv]', '', part)
        if part:
            clean.append(part)
    return clean


def normalize_mixed_code(raw: str) -> list[str]:
    s = re.sub(r'(?<=[a-zv])[1-5](?=$|[^0-9])', '', strip_marks(raw))
    parts = re.split(r"[\s'’·\-_/]+", s)
    clean = []
    for part in parts:
        part = re.sub(r'[^a-z0-9v]', '', part)
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


def looks_numeric(raw: str) -> bool:
    return bool(re.fullmatch(r'\s*[-+]?\d+(?:\.\d+)?%?\s*', raw or ''))


def parse_rime(path: Path):
    body = False
    for lineno, raw in enumerate(path.read_text(encoding='utf-8-sig', errors='replace').splitlines(), 1):
        s = raw.strip()
        if not body:
            if s == '...':
                body = True
            continue
        if not s or s.startswith('#'):
            continue
        f = raw.split('\t')
        if len(f) < 2:
            continue
        word = unicodedata.normalize('NFC', f[0].strip())
        reading = f[1].strip()
        weight = parse_weight(f[2]) if len(f) > 2 else 1.0
        if word and reading:
            yield word, reading, weight, lineno


def parse_english_rime(path: Path):
    """Parse common Rime English table layouts without assuming one exact schema."""
    body = False
    seen = 0
    for lineno, raw in enumerate(path.read_text(encoding='utf-8-sig', errors='replace').splitlines(), 1):
        s = raw.strip()
        if not body:
            if s == '...':
                body = True
            continue
        if not s or s.startswith('#'):
            continue
        f = [x.strip() for x in raw.split('\t')]
        word = unicodedata.normalize('NFC', f[0])
        if not re.fullmatch(r"[A-Za-z][A-Za-z'\-]{2,23}", word):
            continue
        if len(f) >= 2 and looks_numeric(f[1]):
            reading, weight = word, parse_weight(f[1])
        else:
            reading = f[1] if len(f) >= 2 and f[1] else word
            weight = parse_weight(f[2]) if len(f) >= 3 else 1.0
        alias = re.sub(r'[^a-z]', '', reading.lower())
        display = word.lower()
        if len(alias) < 3:
            continue
        seen += 1
        yield display, alias, weight, lineno, seen


def parse_latin_terms(path: Path):
    """Yield (display, lexicon_word, weight, aliases) from curated TSV."""
    for lineno, raw in enumerate(path.read_text(encoding='utf-8-sig', errors='replace').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        fields = raw.split('\t')
        display = unicodedata.normalize('NFC', fields[0].strip())
        if not display:
            raise SystemExit(f'{path}:{lineno}: empty Latin display term')
        weight = parse_weight(fields[1]) if len(fields) > 1 and fields[1].strip() else 100000.0
        aliases_raw = fields[2] if len(fields) > 2 else display
        aliases = []
        for alias in re.split(r'[,;\s]+', aliases_raw.strip()):
            alias = unicodedata.normalize('NFC', alias).lower()
            alias = re.sub(r'[^a-z0-9]+', '', alias)
            if alias and alias not in aliases:
                aliases.append(alias)
        exact = re.sub(r'[^a-z0-9]+', '', display.lower())
        if exact and exact not in aliases:
            aliases.insert(0, exact)
        if not aliases:
            raise SystemExit(f'{path}:{lineno}: no usable aliases for {display!r}')
        # CLEX entries cannot contain whitespace. Keep the display form for
        # CIME, but store a compact normalized token in CLEX.
        lexicon_word = exact or aliases[0]
        yield display, lexicon_word, weight, aliases


def parse_custom_terms(path: Path):
    """candidate<TAB>reading<TAB>weight, allowing Chinese/Latin/mixed candidates."""
    for lineno, raw in enumerate(path.read_text(encoding='utf-8-sig', errors='replace').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        f = raw.split('\t')
        if len(f) < 2:
            raise SystemExit(f'{path}:{lineno}: expected candidate<TAB>reading[<TAB>weight]')
        word = unicodedata.normalize('NFC', f[0].strip())
        reading = f[1].strip()
        weight = parse_weight(f[2]) if len(f) > 2 else 1000.0
        if word and reading:
            yield word, reading, weight, lineno


def source_name(path: Path) -> str:
    # CHANGE (lite): lite-dicts.zip ships "diming.lite.dict.yaml"; strip the
    # ".lite" infix so names match SPECIAL_SOURCES / TOLERANCE_SOURCES and the
    # jichu core-compact budget below.
    name = path.name
    if name.endswith('.dict.yaml'):
        name = name[:-len('.dict.yaml')]
    if name.endswith('.lite'):
        name = name[:-len('.lite')]
        return name
    return name if name != path.name else path.stem


def word_score(word: str, weight: float) -> float:
    score = weight
    if len(word) == 1 and cjk_only(word):
        if ord(word) > 0xFFFF:
            score *= 0.001
        if weight < 5:
            score *= 0.02
        elif weight < 20:
            score *= 0.08
        elif weight < 100:
            score *= 0.25
    return score


def synthetic_english_frequency(rank: int, raw_weight: float) -> float:
    # Keep useful spelling/completion evidence without letting the English table
    # dominate a Chinese pack's unigram distribution.
    rank_component = max(20.0, 2400.0 / math.sqrt(rank + 1))
    weight_component = min(1200.0, max(1.0, math.log10(max(10.0, raw_weight)) * 180.0))
    return max(rank_component, weight_component)


def build_cngm(code: str, ordered_words: list[str], freqs: dict[str, float], out: Path, max_following: int = 48):
    ids = {w:i for i,w in enumerate(ordered_words)}
    pair_counts: dict[tuple[str,str], float] = collections.defaultdict(float)

    for phrase, raw_weight in freqs.items():
        if len(phrase) < 2 or len(phrase) > 16 or not cjk_only(phrase):
            continue
        strength = math.sqrt(max(1.0, raw_weight))
        chars = list(phrase)
        for a,b in zip(chars, chars[1:]):
            if a in ids and b in ids:
                pair_counts[(a,b)] += strength

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
    for (prev,_),_count in ranked:
        blob += struct.pack('<I', ids[prev])
    for (_,following),_count in ranked:
        blob += struct.pack('<I', ids[following])
    for (prev,_), count in ranked:
        probability = count / totals[prev]
        blob.append(max(0, min(255, round((math.log10(probability) + 6) * 42))))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    print(f'Built {out} with {len(ranked):,} weighted transitions.')


def add_candidate(readings, key: str, candidate: str, score: float, weight: float, seen: int):
    if not key:
        return
    old = readings[key].get(candidate)
    if old is None or score > old[0]:
        readings[key][candidate] = (score, weight, old[2] if old else seen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+', type=Path)
    ap.add_argument('--code', default='zh_wx')
    ap.add_argument('--out-dir', type=Path, default=Path('source'))
    ap.add_argument('--lexicon-limit', type=int, default=300000)
    ap.add_argument('--max-candidates', type=int, default=16)
    ap.add_argument('--max-ime-readings', type=int, default=300000)
    ap.add_argument('--max-word-length', type=int, default=12)
    ap.add_argument('--max-following', type=int, default=48)
    ap.add_argument('--single-char-ime-min-weight', type=float, default=200.0)

    ap.add_argument('--latin-terms', type=Path)
    ap.add_argument('--english-dict', type=Path)
    ap.add_argument('--english-limit', type=int, default=20000)
    ap.add_argument('--english-typo-limit', type=int, default=2500)
    ap.add_argument('--mixed-dict', type=Path)
    ap.add_argument('--custom-terms', type=Path)
    ap.add_argument('--shortcut-terms', type=Path)
    ap.add_argument('--blocklist', type=Path,
                      help='one word per line; matching candidates are dropped '
                           'from every table (simplified-only packs)')
    ap.add_argument('--bulk-abbrevs', type=Path, default=None,
                      help='mined initials-abbrev backfill (word<TAB>spaced reading<TAB>weight); '
                           'merged AFTER auto-jianpin at minimal score so native '
                           'candidates keep their rank and keys')

    ap.add_argument('--jianpin-limit', type=int, default=50000)
    ap.add_argument('--core-compact-reading-budget', type=int, default=450000)
    ap.add_argument('--jianpin-min-weight', type=float, default=20.0)
    ap.add_argument('--jianpin-prefix-min-weight', type=float, default=200.0)
    ap.add_argument('--jianpin-max-syllables', type=int, default=8)
    ap.add_argument('--special-reading-budget', type=int, default=25000)
    ap.add_argument('--long-phrase-reading-budget', type=int, default=30000)
    args = ap.parse_args()

    freqs: dict[str,float] = {}
    readings: dict[str, dict[str, tuple[float,float,int]]] = collections.defaultdict(dict)
    candidate_lexicon: dict[str, str] = {}
    jianpin: dict[str, dict[str, tuple[float,float,int]]] = collections.defaultdict(dict)
    protected: set[str] = {
        'pin', 'yin', 'pinyin', 'pin yin',
        'nihao', 'ni hao', 'meiyou', 'mei you',
        'zenme', 'zen me', 'zenmehuishi', 'zen me hui shi',
        'weishenme', 'wei shen me',
        'buzhidao', 'bu zhi dao', 'keyi', 'ke yi',
        'xianzai', 'xian zai', 'jintian', 'jin tian',
        'mingtian', 'ming tian', 'zhongwen', 'zhong wen',
        'shurufa', 'shu ru fa', 'suoyi', 'suo yi',
    }
    blocked: set[str] = set()
    if args.blocklist:
        if not args.blocklist.is_file():
            raise SystemExit(f'Blocklist file not found: {args.blocklist}')
        for raw in args.blocklist.read_text(encoding='utf-8-sig', errors='replace').splitlines():
            line = raw.strip()
            if line and not line.startswith('#'):
                blocked.add(unicodedata.normalize('NFC', line))
        print(f'Loaded {len(blocked):,} blocklisted words from {args.blocklist}.')
    special_scores: dict[str, float] = {}
    long_scores: dict[str, float] = {}
    # Normal compact Pinyin from Wanxiang jichu is the backbone of the pack.
    # Track it separately so feature layers (jianpin/English/typos/etc.) cannot
    # crowd ordinary words out of the finite CIME reading budget.
    core_compact_scores: dict[str, float] = {}
    seen = 0

    for path in args.inputs:
        if not path.is_file():
            raise SystemExit(f'Required input not found: {path}')
        src = source_name(path)
        print(f'Reading {path} ({src}) ...')
        for word, raw_reading, weight, _lineno in parse_rime(path):
            if not cjk_only(word):
                continue
            if args.max_word_length and len(word) > args.max_word_length:
                continue
            # CHANGE (lite): skip rows whose code column still contains CJK
            # (upstream placeholder for a rare character with no pinyin,
            # e.g. code "duan xu 𱇮"); the truncated reading would be wrong.
            if CJK_IN_CODE.search(raw_reading):
                continue
            syllables = normalize_pinyin(raw_reading)
            if not syllables:
                continue
            compact = ''.join(syllables)
            spaced = ' '.join(syllables)
            seen += 1
            freqs[word] = max(freqs.get(word, 0.0), weight)
            score = word_score(word, weight)
            if len(word) == 1 and weight < args.single_char_ime_min_weight:
                continue

            keys = {compact, spaced} if len(syllables) > 1 else {compact}
            if src == 'jichu':
                core_compact_scores[compact] = max(core_compact_scores.get(compact, 0.0), score)
            for key in keys:
                add_candidate(readings, key, word, score, weight, seen)
                if src in TOLERANCE_SOURCES:
                    protected.add(key)
                if src in SPECIAL_SOURCES:
                    special_scores[key] = max(special_scores.get(key, 0.0), score)
                if src == 'lianxiang' or len(syllables) >= 5:
                    long_scores[key] = max(long_scores.get(key, 0.0), score)

            if 2 <= len(syllables) <= args.jianpin_max_syllables and weight >= args.jianpin_min_weight:
                initials = ''.join(part[0] for part in syllables)
                jscore = score * (1.0 + min(6, len(syllables)) * 0.04)
                add_candidate(jianpin, initials, word, jscore, weight, seen)
                # For high-frequency phrases with 4+ syllables, also allow a
                # 3+ initial prefix: zmh -> 怎么回事, while full zmhs still works.
                if len(initials) >= 4 and weight >= args.jianpin_prefix_min_weight:
                    for n in range(3, len(initials)):
                        add_candidate(jianpin, initials[:n], word, jscore * 0.92, weight, seen)

    if not freqs:
        raise SystemExit('No usable Wanxiang entries were parsed.')

    normal_chinese_keys = set(readings)

    # Wanxiang mixed table: Github仓库 / 3A游戏 / QQ邮箱 etc.
    if args.mixed_dict:
        if not args.mixed_dict.is_file():
            raise SystemExit(f'Mixed dictionary not found: {args.mixed_dict}')
        print(f'Reading Wanxiang mixed dictionary {args.mixed_dict} ...')
        for word, raw_reading, weight, _lineno in parse_rime(args.mixed_dict):
            if args.max_word_length and len(word) > args.max_word_length + 8:
                continue
            parts = normalize_mixed_code(raw_reading)
            if not parts:
                continue
            seen += 1
            lex = word.lower()
            candidate_lexicon[word] = lex
            freqs[lex] = max(freqs.get(lex, 0.0), max(30.0, weight))
            compact, spaced = ''.join(parts), ' '.join(parts)
            score = max(400.0, weight)
            for key in ({compact, spaced} if len(parts) > 1 else {compact}):
                add_candidate(readings, key, word, score, weight, seen)
                protected.add(key)

    # Project-maintained technical/game/network/slang additions.
    if args.custom_terms:
        if not args.custom_terms.is_file():
            raise SystemExit(f'Custom terms file not found: {args.custom_terms}')
        print(f'Reading project custom terms {args.custom_terms} ...')
        for word, raw_reading, weight, _lineno in parse_custom_terms(args.custom_terms):
            parts = normalize_mixed_code(raw_reading)
            if not parts:
                continue
            seen += 1
            lex = word.lower()
            candidate_lexicon[word] = lex
            freqs[lex] = max(freqs.get(lex, 0.0), max(50.0, weight))
            compact, spaced = ''.join(parts), ' '.join(parts)
            score = max(800.0, weight * 2.0)
            for key in ({compact, spaced} if len(parts) > 1 else {compact}):
                add_candidate(readings, key, word, score, weight, seen)
                protected.add(key)

    # Explicit user shortcuts. These are intentionally stronger than normal
    # jianpin/domain candidates, while keeping ordinary lexicon frequency modest.
    # A spaced shortcut such as "k j z l" generates both "kjzl" and
    # "k j z l", matching Clink's observed syllable/initial segmentation.
    if args.shortcut_terms:
        if not args.shortcut_terms.is_file():
            raise SystemExit(f'Shortcut terms file not found: {args.shortcut_terms}')
        print(f'Reading explicit shortcut terms {args.shortcut_terms} ...')
        for word, raw_reading, weight, _lineno in parse_custom_terms(args.shortcut_terms):
            parts = normalize_mixed_code(raw_reading)
            if not parts:
                continue
            seen += 1
            lex = word.lower()
            candidate_lexicon[word] = lex
            # Do not let a convenience shortcut distort CLEX frequency heavily.
            freqs[lex] = max(freqs.get(lex, 0.0), max(100.0, min(weight, 5000.0)))
            compact, spaced = ''.join(parts), ' '.join(parts)
            for key in ({compact, spaced} if len(parts) > 1 else {compact}):
                add_candidate(readings, key, word, 1_000_000_000.0 + weight, weight, seen)
                protected.add(key)

    # High-frequency English exact words from Wanxiang en.dict.yaml.
    english_exact: set[str] = set()
    english_ranked = []
    if args.english_dict:
        if not args.english_dict.is_file():
            raise SystemExit(f'English dictionary not found: {args.english_dict}')
        english_entries = list(parse_english_rime(args.english_dict))
        english_entries.sort(key=lambda x: (-x[2], x[4], x[0]))
        english_ranked = english_entries[:args.english_limit] if args.english_limit else english_entries
        print(f'Using {len(english_ranked):,} high-frequency English words from {args.english_dict}.')
        for rank, (display, alias, raw_weight, _lineno, _order) in enumerate(english_ranked, 1):
            seen += 1
            english_exact.add(alias)
            synthetic = synthetic_english_frequency(rank, raw_weight)
            candidate_lexicon[display] = display.lower()
            freqs[display.lower()] = max(freqs.get(display.lower(), 0.0), synthetic)
            # Exact English is deliberately moderate: for short collisions such
            # as "you", normal Chinese Pinyin remains competitive/usually first.
            escore = min(1800.0, synthetic)
            add_candidate(readings, alias, display, escore, synthetic, seen)
            protected.add(alias)

    # Curated brands/technical terms preserve casing and carry hand-reviewed typos.
    curated_aliases: set[str] = set()
    if args.latin_terms:
        if not args.latin_terms.is_file():
            raise SystemExit(f'Latin terms file not found: {args.latin_terms}')
        print(f'Reading curated Latin terms {args.latin_terms} ...')
        for display, lexicon_word, weight, aliases in parse_latin_terms(args.latin_terms):
            seen += 1
            freqs[lexicon_word] = max(freqs.get(lexicon_word, 0.0), weight)
            candidate_lexicon[display] = lexicon_word
            exact = re.sub(r'[^a-z0-9]+', '', display.lower())
            for alias in aliases:
                curated_aliases.add(alias)
                # Exact branded spelling is strongest; reviewed typo aliases are
                # still strong but do not alter the lexicon word itself.
                score = weight * (12.0 if alias == exact else 8.0)
                add_candidate(readings, alias, display, score, weight, seen)
                protected.add(alias)

    # Safe automatic English typo aliases. We only use adjacent transpositions
    # and one-character omissions for the most frequent words, and discard any
    # typo that collides with a real English word, a normal Pinyin reading, or
    # more than one source word.
    if english_ranked and args.english_typo_limit:
        proposals: dict[str, set[str]] = collections.defaultdict(set)
        display_by_alias = {alias: display for display, alias, *_ in english_ranked}
        top_aliases = [alias for _display, alias, *_ in english_ranked[:args.english_typo_limit]]
        for alias in top_aliases:
            if len(alias) < 5 or len(alias) > 14:
                continue
            for i in range(len(alias) - 1):
                if alias[i] == alias[i+1]:
                    continue
                typo = alias[:i] + alias[i+1] + alias[i] + alias[i+2:]
                proposals[typo].add(alias)
            for i in range(1, len(alias) - 1):
                typo = alias[:i] + alias[i+1:]
                proposals[typo].add(alias)

        auto_typos = 0
        for typo, origins in sorted(proposals.items()):
            if len(origins) != 1:
                continue
            if typo in english_exact or typo in curated_aliases or typo in normal_chinese_keys:
                continue
            origin = next(iter(origins))
            display = display_by_alias[origin]
            seen += 1
            add_candidate(readings, typo, display, 650.0, 100.0, seen)
            protected.add(typo)
            auto_typos += 1
        print(f'Added {auto_typos:,} collision-filtered automatic English typo aliases.')

    # Add jianpin only after exact Pinyin/English/mixed keys are known. Never
    # replace a real complete reading; exact keys keep their normal meaning.
    jianpin_rows = []
    forbidden_jianpin = set(readings)
    for key, candidates in jianpin.items():
        if key in forbidden_jianpin or len(key) < 2:
            continue
        strongest = max(meta[0] for meta in candidates.values())
        jianpin_rows.append((key, strongest, candidates))
    jianpin_rows.sort(key=lambda item: (-item[1], len(item[0]), item[0]))
    if args.jianpin_limit:
        jianpin_rows = jianpin_rows[:args.jianpin_limit]
    for key, _strongest, candidates in jianpin_rows:
        for word, meta in candidates.items():
            add_candidate(readings, key, word, meta[0], meta[1], meta[2])
        protected.add(key)
    print(f'Added {len(jianpin_rows):,} non-conflicting jianpin readings.')

    # CHANGE (bulk backfill): mined initials abbrevs are merged AFTER the
    # auto-jianpin above, at minimal score, so they can never outrank or
    # block a native candidate for the same reading. A brand-new reading
    # gets the word as its (only) candidate; an existing reading gains it
    # at the tail. (The --shortcut-terms lane carries score 1e9 by design
    # for a handful of hand-picked shortcuts; bulk backfill must not use it.)
    if args.bulk_abbrevs:
        if not args.bulk_abbrevs.is_file():
            raise SystemExit(f'Bulk abbrevs file not found: {args.bulk_abbrevs}')
        print(f'Reading bulk abbrev backfill {args.bulk_abbrevs} ...')
        n_bulk = 0
        for word, raw_reading, weight, _lineno in parse_custom_terms(args.bulk_abbrevs):
            if not cjk_only(word):
                continue
            parts = normalize_mixed_code(raw_reading)
            if not parts:
                continue
            seen += 1
            lex = word.lower()
            candidate_lexicon[word] = lex
            freqs[lex] = max(freqs.get(lex, 0.0), 6000.0)
            compact = ''.join(parts)
            add_candidate(readings, compact, word, 1.0, weight, seen)
            protected.add(compact)
            n_bulk += 1
        print(f'Merged {n_bulk:,} bulk abbrev rows (minimal score, post-jianpin).')

    # Reserve a large compact-only slice for ordinary Wanxiang jichu Pinyin.
    # Compact keys are what users physically type (e.g. dihao). Keeping these
    # before spaced duplicates gives much broader vocabulary coverage at nearly
    # the same package size.
    core_compact_ranked = sorted(
        core_compact_scores,
        key=lambda r: (-core_compact_scores[r], len(r), r),
    )
    if args.core_compact_reading_budget:
        core_compact_ranked = core_compact_ranked[:args.core_compact_reading_budget]
    protected.update(core_compact_ranked)
    print(
        f'Protected {len(core_compact_ranked):,} compact jichu readings '
        f'for baseline Chinese coverage.'
    )

    # Protect the highest-signal names/places and long-phrase readings so a
    # global size budget cannot silently erase these requested categories.
    for key, _score in sorted(special_scores.items(), key=lambda kv: (-kv[1], kv[0]))[:args.special_reading_budget]:
        protected.add(key)
    for key, _score in sorted(long_scores.items(), key=lambda kv: (-kv[1], kv[0]))[:args.long_phrase_reading_budget]:
        protected.add(key)

    # CHANGE (simplified-only): drop blocklisted traditional words from every
    # table before ranking/writing, so the pack ships simplified only.
    if blocked:
        for key in list(readings):
            cands = readings[key]
            for cand in [c for c in cands if c in blocked]:
                del cands[cand]
            if not cands:
                del readings[key]
        for w in [w for w in freqs if w in blocked]:
            del freqs[w]
        for w in [w for w in candidate_lexicon if w in blocked]:
            del candidate_lexicon[w]
        print(f'Excluded {len(blocked):,} blocklisted words from IME tables.')

    ranked_words = sorted(freqs, key=lambda w: (-word_score(w, freqs[w]), -freqs[w], len(w), w))
    keep = set(ranked_words[:args.lexicon_limit] if args.lexicon_limit else ranked_words)
    keep.update(w for w in freqs if len(w) == 1 and cjk_only(w))

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
        mandatory = [r for r in reading_order if r in protected]
        if len(mandatory) > args.max_ime_readings:
            raise SystemExit(
                f'Protected reading set ({len(mandatory):,}) exceeds IME budget '
                f'({args.max_ime_readings:,}); raise the budget instead of silently dropping features.'
            )
        chosen = set(mandatory)
        for r in reading_order:
            if len(chosen) >= args.max_ime_readings:
                break
            chosen.add(r)
        reading_order = [r for r in reading_order if r in chosen]

    ime_rows = {}
    for reading in reading_order:
        candidates = readings[reading]
        ranked = sorted(candidates.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[1][2], kv[0]))
        top = [w for w,_ in ranked[:args.max_candidates]]
        if top:
            ime_rows[reading] = top
            keep.update(candidate_lexicon.get(w, w).lower() for w in top)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    lex_path = args.out_dir / f'{args.code}.txt'
    ime_path = args.out_dir / f'{args.code}-ime.tsv'

    with lex_path.open('w', encoding='utf-8', newline='\n') as f:
        f.write('# word<TAB>frequency — Wanxiang-derived Clink data\n')
        for word in sorted(keep, key=lambda w: (-freqs.get(w,1.0), w)):
            f.write(f'{word}\t{freqs.get(word,1.0):g}\n')

    with ime_path.open('w', encoding='utf-8', newline='\n') as f:
        f.write('# reading<TAB>candidate... — full Pinyin, jianpin, mixed and English keys\n')
        for reading in sorted(ime_rows):
            f.write('\t'.join([reading, *ime_rows[reading]]) + '\n')

    ordered = sorted(keep, key=lambda w: w.encode('utf-8'))
    build_cngm(args.code, ordered, freqs, Path('Lexicons')/f'{args.code}.cngm', args.max_following)

    print(f'Lexicon words: {len(keep):,}')
    print(f'IME readings:  {len(ime_rows):,}')
    for probe in (
        'pin','pinyin','pin yin','nihao','ni hao','bzd','wsm','zmhs','zmh',
        'github','githbu','computer','pyhton','githubcangku','yyds'
    ):
        print(probe, '=>', ' / '.join(ime_rows.get(probe, [])[:8]) or 'MISSING')


if __name__ == '__main__':
    main()
