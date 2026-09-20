#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production wrapper for Clink Chinese Wanxiang dict-nightly builds.

It discovers the Chinese tables actually present in Wanxiang's rolling
base-dicts.zip, requires the core zi/jichu/lianxiang tables, excludes non-Chinese
auxiliary tables, then delegates normalization/ranking/CNGM generation to the
already-tested v2 converter while switching the production language code to zh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PREFERRED_TABLES = [
    "zi", "jichu", "lianxiang", "cuoyin", "duoyin", "shici", "diming",
    "yixue", "huaxue", "yaopin", "mingren", "yiren", "wuzhong",
    "renming", "taifeng", "fangyan",
]
CORE_TABLES = {"zi", "jichu", "lianxiang"}
EXCLUDED_TABLES = {"abbrev", "t9_abbrev", "en", "mixed"}
FINGERPRINT_MARKERS = {"万象验证甲", "万象验证乙", "万象验证丙"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def locate_one(root: Path, filename: str) -> Path:
    matches = list(root.rglob(filename))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one {filename} under {root}; found {len(matches)}")
    return matches[0]


def locate(root: Path) -> list[tuple[str, Path]]:
    by_name: dict[str, Path] = {}
    for path in root.rglob("*.dict.yaml"):
        name = path.name.removesuffix(".dict.yaml")
        if name in EXCLUDED_TABLES:
            continue
        if name in by_name:
            raise SystemExit(f"Duplicate {name}.dict.yaml under {root}")
        by_name[name] = path

    missing_core = sorted(CORE_TABLES - set(by_name))
    if missing_core:
        raise SystemExit(f"dict-nightly base asset is missing core tables: {missing_core}")

    ordered_names = [name for name in PREFERRED_TABLES if name in by_name]
    ordered_names += sorted(set(by_name) - set(ordered_names))
    return [(name, by_name[name]) for name in ordered_names]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dict-root", type=Path, required=True)
    p.add_argument("--code", default="zh")
    p.add_argument("--out-dir", type=Path, default=Path("source"))
    p.add_argument("--lexicon-limit", type=int, default=600000)
    p.add_argument("--max-ime-readings", type=int, default=400000)
    p.add_argument("--max-candidates", type=int, default=16)
    p.add_argument("--max-word-length", type=int, default=16)
    p.add_argument("--max-following", type=int, default=64)
    p.add_argument("--single-char-ime-min-weight", type=float, default=1.0)
    p.add_argument("--latin-terms", type=Path, default=Path("source/zh-latin-terms.tsv"))
    p.add_argument("--custom-terms", type=Path, default=Path("source/zh-domain-terms.tsv"))
    p.add_argument("--shortcut-terms", type=Path, default=Path("source/zh-shortcuts.tsv"))
    p.add_argument("--english-limit", type=int, default=20000)
    p.add_argument("--english-typo-limit", type=int, default=2500)
    p.add_argument("--jianpin-limit", type=int, default=50000)
    p.add_argument("--receipt-json", type=Path)
    args = p.parse_args()

    table_items = locate(args.dict_root)
    tables = [path for _name, path in table_items]
    english_dict = locate_one(args.dict_root, "en.dict.yaml")
    mixed_dict = locate_one(args.dict_root, "mixed.dict.yaml")
    delegate = Path(__file__).with_name("build_zh_wanxiang_v2.py")
    if not delegate.is_file():
        raise SystemExit(f"Missing delegate builder: {delegate}")

    command = [
        sys.executable, str(delegate), *map(str, tables),
        "--code", args.code,
        "--out-dir", str(args.out_dir),
        "--lexicon-limit", str(args.lexicon_limit),
        "--max-ime-readings", str(args.max_ime_readings),
        "--max-candidates", str(args.max_candidates),
        "--max-word-length", str(args.max_word_length),
        "--max-following", str(args.max_following),
        "--single-char-ime-min-weight", str(args.single_char_ime_min_weight),
        "--english-dict", str(english_dict),
        "--english-limit", str(args.english_limit),
        "--english-typo-limit", str(args.english_typo_limit),
        "--mixed-dict", str(mixed_dict),
        "--jianpin-limit", str(args.jianpin_limit),
    ]
    if args.latin_terms:
        if not args.latin_terms.is_file():
            raise SystemExit(f"Missing curated Latin terms file: {args.latin_terms}")
        command += ["--latin-terms", str(args.latin_terms)]
    if args.custom_terms:
        if not args.custom_terms.is_file():
            raise SystemExit(f"Missing custom terms file: {args.custom_terms}")
        command += ["--custom-terms", str(args.custom_terms)]
    if args.shortcut_terms:
        if not args.shortcut_terms.is_file():
            raise SystemExit(f"Missing shortcut terms file: {args.shortcut_terms}")
        command += ["--shortcut-terms", str(args.shortcut_terms)]
    subprocess.run(command, check=True)

    ime = args.out_dir / f"{args.code}-ime.tsv"
    text = ime.read_text(encoding="utf-8")
    leaked = sorted(marker for marker in FINGERPRINT_MARKERS if marker in text)
    if leaked:
        raise SystemExit(f"Diagnostic fingerprint leaked into production IME: {leaked}")

    if args.receipt_json:
        receipt = {
            "builderVersion": 3,
            "code": args.code,
            "delegate": delegate.name,
            "nightlyAuxiliaryTables": [
                {
                    "name": "en",
                    "path": str(english_dict),
                    "sha256": sha256(english_dict),
                    "byteCount": english_dict.stat().st_size,
                },
                {
                    "name": "mixed",
                    "path": str(mixed_dict),
                    "sha256": sha256(mixed_dict),
                    "byteCount": mixed_dict.stat().st_size,
                },
            ],
            "latinTerms": ({
                "path": str(args.latin_terms),
                "sha256": sha256(args.latin_terms),
                "byteCount": args.latin_terms.stat().st_size,
            } if args.latin_terms else None),
            "customTerms": ({
                "path": str(args.custom_terms),
                "sha256": sha256(args.custom_terms),
                "byteCount": args.custom_terms.stat().st_size,
            } if args.custom_terms else None),
            "shortcutTerms": ({
                "path": str(args.shortcut_terms),
                "sha256": sha256(args.shortcut_terms),
                "byteCount": args.shortcut_terms.stat().st_size,
            } if args.shortcut_terms else None),
            "standardTables": [
                {
                    "name": name,
                    "path": str(path),
                    "sha256": sha256(path),
                    "byteCount": path.stat().st_size,
                }
                for name, path in table_items
            ],
            "limits": {
                "lexiconLimit": args.lexicon_limit,
                "maxImeReadings": args.max_ime_readings,
                "maxCandidates": args.max_candidates,
                "maxWordLength": args.max_word_length,
                "maxFollowing": args.max_following,
                "singleCharImeMinWeight": args.single_char_ime_min_weight,
                "englishLimit": args.english_limit,
                "englishTypoLimit": args.english_typo_limit,
                "jianpinLimit": args.jianpin_limit,
            },
        }
        args.receipt_json.parent.mkdir(parents=True, exist_ok=True)
        args.receipt_json.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print("Production tables:", ", ".join(name for name, _path in table_items))
    print("IME TSV bytes:", ime.stat().st_size)


if __name__ == "__main__":
    main()
