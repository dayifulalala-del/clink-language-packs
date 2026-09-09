#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Rime/Wanxiang dictionaries (*.dict.yaml) into Clink Chinese source files.

Primary output:
  source/zh-ime.tsv -> tools/build-ime-table.py -> Lexicons/zh.cime

The generated zh.txt is also retained for future CLEX experiments, but this
v1 workflow intentionally does NOT replace Clink's official zh.clex because
the existing zh.cngm model is indexed against that dictionary.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

TONE_UMLAUT = str.maketrans({
    "ü": "v", "ǖ": "v", "ǘ": "v", "ǚ": "v", "ǜ": "v",
    "Ü": "v", "Ǖ": "v", "Ǘ": "v", "Ǚ": "v", "Ǜ": "v",
})
CJK_RANGES = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0x20000, 0x2FA1F),
)

def has_cjk(text: str) -> bool:
    return any(any(lo <= ord(ch) <= hi for lo, hi in CJK_RANGES) for ch in text)

def normalize_reading(reading: str) -> str:
    reading = unicodedata.normalize("NFC", reading.strip()).translate(TONE_UMLAUT)
    reading = reading.replace("u:", "v").replace("U:", "v")
    reading = unicodedata.normalize("NFD", reading)
    reading = "".join(ch for ch in reading if unicodedata.category(ch) != "Mn")
    reading = unicodedata.normalize("NFC", reading).lower()
    reading = re.sub(r"[1-5]", "", reading)
    reading = re.sub(r"[\s'’·\-_/]+", "", reading)
    return reading if re.fullmatch(r"[a-zv]+", reading or "") else ""

def parse_weight(raw: str) -> float:
    raw = raw.strip()
    if not raw:
        return 1.0
    if raw.endswith("%"):
        raw = raw[:-1]
    try:
        value = float(raw)
    except ValueError:
        m = re.match(r"[-+]?\d+(?:\.\d+)?", raw)
        if not m:
            return 1.0
        value = float(m.group(0))
    return value if math.isfinite(value) and value > 0 else 1.0

def iter_input_files(paths: list[Path]):
    seen = set()
    for path in paths:
        if path.is_dir():
            files = sorted(path.rglob("*.dict.yaml"))
            if not files:
                raise SystemExit(f"No *.dict.yaml inputs found in: {path}")
        elif path.is_file():
            files = [path]
        else:
            raise SystemExit(f"Required input not found: {path}")
        for file in files:
            key = file.resolve()
            if key not in seen:
                seen.add(key)
                yield file

def parse_rime_file(path: Path):
    in_body = False
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for line_no, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not in_body:
            if stripped == "...":
                in_body = True
            continue
        if not stripped or stripped.startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) < 2:
            continue
        word = unicodedata.normalize("NFC", fields[0].strip())
        reading = fields[1].strip()
        weight = parse_weight(fields[2]) if len(fields) >= 3 else 1.0
        if word and reading:
            yield word, reading, weight, line_no

def load_seed_cime(path: Path | None) -> dict[str, list[str]]:
    seed: dict[str, list[str]] = {}
    if not path:
        return seed
    if not path.exists():
        raise SystemExit(f"Seed CIME not found: {path}")
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        fields = [unicodedata.normalize("NFC", x.strip()) for x in raw.split("\t")]
        if len(fields) < 2:
            continue
        reading = normalize_reading(fields[0])
        candidates = [x for x in fields[1:] if x]
        if reading and candidates:
            seed[reading] = list(dict.fromkeys(candidates))
    return seed

def main():
    ap = argparse.ArgumentParser(description="Rime/Wanxiang -> Clink Chinese IME table")
    ap.add_argument("inputs", nargs="+", type=Path,
                    help="*.dict.yaml files or directories")
    ap.add_argument("--out-dir", type=Path, default=Path("source"))
    ap.add_argument("--seed-cime", type=Path,
                    help="Existing Clink zh.cime used only as a fallback")
    ap.add_argument("--max-candidates", type=int, default=16)
    ap.add_argument("--max-readings", type=int, default=250000,
                    help="Global reading budget; seed readings are always preserved. 0 = unlimited.")
    ap.add_argument("--max-word-length", type=int, default=12,
                    help="Discard implausibly long candidates. 0 = unlimited.")
    ap.add_argument("--min-weight", type=float, default=1.0)
    args = ap.parse_args()

    readings: dict[str, dict[str, tuple[float, int]]] = defaultdict(dict)
    words: dict[str, float] = {}
    seen_counter = accepted = skipped = 0

    for file in iter_input_files(args.inputs):
        print(f"Reading {file} ...")
        for word, raw_reading, weight, _line_no in parse_rime_file(file):
            if weight < args.min_weight:
                skipped += 1
                continue
            if not has_cjk(word) or any(ch.isspace() for ch in word):
                skipped += 1
                continue
            if args.max_word_length and len(word) > args.max_word_length:
                skipped += 1
                continue
            reading = normalize_reading(raw_reading)
            if not reading:
                skipped += 1
                continue

            seen_counter += 1
            accepted += 1
            old = readings[reading].get(word)
            if old is None or weight > old[0]:
                readings[reading][word] = (weight, old[1] if old else seen_counter)
            words[word] = max(words.get(word, 0.0), weight)

    seed = load_seed_cime(args.seed_cime)

    all_readings = set(readings) | set(seed)
    if args.max_readings and len(all_readings) > args.max_readings:
        keep = set(seed)
        room = max(0, args.max_readings - len(keep))
        extras = [r for r in readings if r not in keep]
        extras.sort(
            key=lambda r: (
                -max((meta[0] for meta in readings[r].values()), default=0.0),
                r,
            )
        )
        keep.update(extras[:room])
    else:
        keep = all_readings

    args.out_dir.mkdir(parents=True, exist_ok=True)
    ime_path = args.out_dir / "zh-ime.tsv"
    lex_path = args.out_dir / "zh.txt"

    with ime_path.open("w", encoding="utf-8", newline="\n") as out:
        out.write("# Wanxiang-enhanced Clink Chinese IME table\n")
        for reading in sorted(keep):
            ranked = sorted(
                readings.get(reading, {}).items(),
                key=lambda item: (-item[1][0], item[1][1], item[0]),
            )
            candidates = [word for word, _meta in ranked]
            for word in seed.get(reading, []):
                if word not in candidates:
                    candidates.append(word)
            candidates = candidates[:args.max_candidates]
            if candidates:
                out.write("\t".join([reading, *candidates]) + "\n")

    with lex_path.open("w", encoding="utf-8", newline="\n") as out:
        out.write("# word<TAB>frequency -- generated for future experiments\n")
        for word, weight in sorted(words.items(), key=lambda x: (-x[1], x[0])):
            out.write(f"{word}\t{weight:g}\n")

    ime_size = ime_path.stat().st_size
    print()
    print(f"Entries accepted: {accepted:,}")
    print(f"Entries skipped:  {skipped:,}")
    print(f"Wanxiang readings:{len(readings):,}")
    print(f"Seed readings:    {len(seed):,}")
    print(f"Output readings:  {len(keep):,}")
    print(f"Unique words:     {len(words):,}")
    print(f"zh-ime.tsv size:  {ime_size / 1024 / 1024:.2f} MiB")
    print(f"Wrote: {ime_path}")
    print(f"Wrote: {lex_path}")

if __name__ == "__main__":
    main()
