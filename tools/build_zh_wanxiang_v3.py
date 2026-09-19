#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production wrapper for Clink Chinese Wanxiang dict-nightly builds.

It discovers exactly the standard tables imported by Wanxiang's base
wanxiang.dict.yaml, then delegates normalization/ranking/CNGM generation to the
already-tested v2 converter while switching the production language code to zh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

STANDARD_TABLES = [
    "zi", "jichu", "lianxiang", "cuoyin", "duoyin", "shici", "diming",
    "yixue", "huaxue", "yaopin", "mingren", "yiren", "wuzhong",
    "renming", "taifeng", "fangyan",
]
FINGERPRINT_MARKERS = {"万象验证甲", "万象验证乙", "万象验证丙"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def locate(root: Path) -> list[Path]:
    result = []
    for name in STANDARD_TABLES:
        matches = list(root.rglob(f"{name}.dict.yaml"))
        if len(matches) != 1:
            raise SystemExit(
                f"Expected exactly one {name}.dict.yaml under {root}; found {len(matches)}"
            )
        result.append(matches[0])
    return result


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
    p.add_argument("--receipt-json", type=Path)
    args = p.parse_args()

    tables = locate(args.dict_root)
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
            "standardTables": [
                {
                    "name": name,
                    "path": str(path),
                    "sha256": sha256(path),
                    "byteCount": path.stat().st_size,
                }
                for name, path in zip(STANDARD_TABLES, tables)
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

    print("Production tables:", ", ".join(STANDARD_TABLES))
    print("IME TSV bytes:", ime.stat().st_size)


if __name__ == "__main__":
    main()
