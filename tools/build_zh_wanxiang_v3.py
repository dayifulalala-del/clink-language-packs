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
    p.add_argument("--receipt-json", type=Path)
    args = p.parse_args()

    table_items = locate(args.dict_root)
    tables = [path for _name, path in table_items]
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
    ]
    if args.latin_terms:
        if not args.latin_terms.is_file():
            raise SystemExit(f"Missing curated Latin terms file: {args.latin_terms}")
        command += ["--latin-terms", str(args.latin_terms)]
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
            "latinTerms": ({
                "path": str(args.latin_terms),
                "sha256": sha256(args.latin_terms),
                "byteCount": args.latin_terms.stat().st_size,
            } if args.latin_terms else None),
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
