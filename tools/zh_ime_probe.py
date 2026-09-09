#!/usr/bin/env python3
"""Build/verify a controlled zh A/B probe, not a simulation of the iOS IME.

Keep the published v2 CLEX/CNGM pair byte-identical. Only replace the CIME pin
row. All downloaded baseline bytes are pinned independently of GitHub latest.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import sys
import urllib.request

BASE_REPO = "dayifulalala-del/clink-language-packs"
BASE_TAG = "vzh-wx-v2-1-1"
BASE_URL = f"https://github.com/{BASE_REPO}/releases/download/{BASE_TAG}"
BASE = {
    "cime": (7962180, "69176f8acb9001a3946abbadc6128cb8165c8d06bfe211d76cfe303a2eb866d9"),
    "clex": (5779667, "541fa81f34bcaabd68813936cc446be3410ea1837a828f252af8557a9217ecd8"),
    "cngm": (7616460, "e08dbdac24732c9dab12640bad973f63ecadaeb597aa831a3aa21e98dbb0f243"),
}
MARKERS = {"A": "拼", "B": "榀"}
COMMON = {
    "pinyin": "拼音", "pin yin": "拼音", "nihao": "你好", "ni hao": "你好",
    "meiyou": "没有", "mei you": "没有", "zenmehuishi": "怎么回事",
    "zen me hui shi": "怎么回事", "weishenme": "为什么", "wei shen me": "为什么",
    "buzhidao": "不知道", "bu zhi dao": "不知道", "zhongwen": "中文",
    "zhong wen": "中文", "shurufa": "输入法", "shu ru fa": "输入法",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "clink-zh-ime-probe"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def decode_cime(data):
    require(data.endswith(b"\n") and b"\r" not in data, "CIME must use final LF")
    rows = {}
    for line in data.decode("utf-8").splitlines():
        fields = line.split("\t")
        require(2 <= len(fields) <= 17 and all(fields), "Invalid CIME fields/candidate cap")
        key, *candidates = fields
        require(key == key.strip().lower() and key not in rows, "Invalid/duplicate reading")
        require(len(set(candidates)) == len(candidates), "Duplicate candidate")
        rows[key] = candidates
    require(list(rows) == sorted(rows), "CIME readings out of order")
    return rows


def patch_pin(data, variant):
    # Preserve every other byte, including candidate order and spaced readings.
    rows = decode_cime(data)
    require("pin" in rows, "Missing baseline pin")
    result = b"".join(
        ("pin\t" + MARKERS[variant] + "\n").encode("utf-8")
        if line.startswith(b"pin\t") else line
        for line in data.splitlines(keepends=True)
    )
    changed = decode_cime(result)
    require(changed["pin"] == [MARKERS[variant]], "Wrong marker")
    require({k: v for k, v in changed.items() if k != "pin"} ==
            {k: v for k, v in rows.items() if k != "pin"}, "Unexpected CIME change")
    return result


def decode_clex(data):
    magic, version, count, alphabet = struct.unpack_from("<4sIII", data)
    require(magic == b"CLEX" and version == 1 and 0 < alphabet <= 48, "Invalid CLEX header")
    pos = 16 + alphabet * 4 + (alphabet + 1) * alphabet
    offsets = struct.unpack_from(f"<{count + 1}I", data, pos)
    pos += (count + 1) * 4
    lengths = data[pos + count:pos + 2 * count]
    pos += 2 * count
    require(offsets[0] == 0 and pos + offsets[-1] == len(data), "Invalid CLEX offsets/end")
    require(all(a < b for a, b in zip(offsets, offsets[1:])), "Non-increasing CLEX offsets")
    words = [data[pos + a:pos + b].decode("utf-8") for a, b in zip(offsets, offsets[1:])]
    require(words == sorted(set(words), key=lambda w: w.encode("utf-8")), "Wrong CLEX word order")
    require(len(lengths) == count and all(min(len(w), 255) == n for w, n in zip(words, lengths)),
            "Wrong CLEX lengths")
    return words


def check_cngm(data, word_count):
    magic, version, count = struct.unpack_from("<4sII", data)
    require(magic == b"CNGM" and version == 1 and len(data) == 12 + count * 9, "Invalid CNGM")
    previous = struct.unpack_from(f"<{count}I", data, 12)
    following = struct.unpack_from(f"<{count}I", data, 12 + count * 4)
    scores = data[12 + count * 8:]
    require(all(i < word_count for i in previous + following), "CNGM word ID out of range")
    require(all(a <= b for a, b in zip(previous, previous[1:])), "CNGM groups out of order")
    require(all(previous[i] != previous[i + 1] or scores[i] >= scores[i + 1]
                for i in range(count - 1)), "CNGM group scores out of order")
    return count


def check_payload(blobs, variant):
    require(set(blobs) == set(BASE), "Unexpected assets; neural models must be absent")
    for ext in ("clex", "cngm"):
        require((len(blobs[ext]), digest(blobs[ext])) == BASE[ext], f"Changed matched {ext}")
    words = decode_clex(blobs["clex"])
    require(set(MARKERS.values()) <= set(words), "Both A/B markers must exist in unchanged CLEX")
    pairs = check_cngm(blobs["cngm"], len(words))
    rows = decode_cime(blobs["cime"])
    require(len(rows) == 300000, "Unexpected reading count")
    require(rows["pin"] == [MARKERS[variant]], "Wrong pin marker")
    require(all(rows.get(k, [None])[0] == v for k, v in COMMON.items()), "Common reading regression")
    candidates = {word for values in rows.values() for word in values}
    require(candidates <= set(words), "CIME candidate missing from matched CLEX")
    return {"variant": variant, "pin": rows["pin"], "words": len(words), "readings": len(rows),
            "next_word_pairs": pairs, "sha256": {k: digest(v) for k, v in blobs.items()},
            "byteCount": {k: len(v) for k, v in blobs.items()},
            "device_ime_activation": "NOT TESTED"}


def check_manifest(manifest, repository, version, blobs):
    require(set(manifest) == {"version", "packs"} and manifest["version"] == version, "Wrong manifest")
    require(len(manifest["packs"]) == 1, "Expected exactly one pack")
    pack = manifest["packs"][0]
    require(set(pack) == {"code", "version", "assets"} and pack["code"] == "zh"
            and pack["version"] == version, "Wrong pack metadata")
    require([a["path"] for a in pack["assets"]] == ["zh.cime", "zh.clex", "zh.cngm"], "Wrong asset set")
    for asset in pack["assets"]:
        ext = asset["path"].split(".")[-1]
        require(asset["url"] == f"https://github.com/{repository}/releases/download/{version}/zh--zh.{ext}",
                "Wrong repository/tag/asset URL")
        require(asset["sha256"] == digest(blobs[ext]) and asset["byteCount"] == len(blobs[ext]),
                "Manifest hash/size mismatch")


def build(stage, repository, version, variant):
    # Refuse to mix with old/stale output; never delete any existing directory.
    stage.mkdir(parents=True, exist_ok=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        blobs = dict(zip(BASE, pool.map(lambda ext: download(f"{BASE_URL}/zh_wx--zh_wx.{ext}"), BASE)))
    for ext, data in blobs.items():
        require((len(data), digest(data)) == BASE[ext], f"Baseline checksum failed: {ext}")
    a, b = (patch_pin(blobs["cime"], v) for v in ("A", "B"))
    a_lines, b_lines = a.splitlines(), b.splitlines()
    require(len(a_lines) == len(b_lines), "A/B row count changed")
    diffs = [(x, y) for x, y in zip(a_lines, b_lines) if x != y]
    require(diffs == [("pin\t拼".encode(), "pin\t榀".encode())], "A/B must differ only at pin")
    blobs["cime"] = a if variant == "A" else b
    report = check_payload(blobs, variant)
    root = pathlib.Path(__file__).resolve().parents[1]
    (stage / "Lexicons").mkdir()
    (stage / "tools").mkdir()
    (stage / "catalog").mkdir()
    for ext, data in blobs.items():
        (stage / f"Lexicons/zh.{ext}").write_bytes(data)
    for name in ("build-release-manifest.py", "validate-pack.py"):
        shutil.copy2(root / "tools" / name, stage / "tools" / name)
    shutil.copy2(root / "catalog/language-wave.json", stage / "catalog/language-wave.json")
    subprocess.run([sys.executable, str(stage / "tools/validate-pack.py"), "zh"], cwd=stage, check=True)
    subprocess.run([sys.executable, str(stage / "tools/build-release-manifest.py"),
                    version, repository, str(stage / "out")], check=True)
    manifest = json.loads((stage / "out/manifest.json").read_bytes())
    check_manifest(manifest, repository, version, blobs)
    report.update(baseline_tag=BASE_TAG, ab_changed_readings=["pin"],
                  variant_cime_sha256={"A": digest(a), "B": digest(b)},
                  manifest_sha256=digest((stage / "out/manifest.json").read_bytes()))
    (stage / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def verify_release(repository, version, variant, expected_manifest):
    base = f"https://github.com/{repository}/releases/download/{version}"
    manifest_bytes = download(f"{base}/manifest.json")
    if expected_manifest:
        require(manifest_bytes == expected_manifest.read_bytes(), "Remote manifest differs from build")
    # Do not follow unvalidated manifest URLs.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        blobs = dict(zip(BASE, pool.map(lambda ext: download(f"{base}/zh--zh.{ext}"), BASE)))
    check_manifest(json.loads(manifest_bytes), repository, version, blobs)
    # Independent reconstruction from pinned baseline proves every non-pin row unchanged.
    baseline = download(f"{BASE_URL}/zh_wx--zh_wx.cime")
    require((len(baseline), digest(baseline)) == BASE["cime"], "Invalid CIME baseline")
    require(blobs["cime"] == patch_pin(baseline, variant), "Remote CIME differs from controlled probe")
    latest = json.loads(download(f"https://api.github.com/repos/{repository}/releases/latest"))
    listed = json.loads(download(f"https://api.github.com/repos/{repository}/releases?per_page=1"))
    require(latest["tag_name"] == version and listed[0]["tag_name"] == version,
            f"Release discovery disagreement: latest={latest['tag_name']}, first={listed[0]['tag_name']}")
    require(not latest["draft"] and not latest["prerelease"], "Release not public/stable")
    require({a["name"] for a in latest["assets"]} ==
            {"manifest.json", "zh--zh.cime", "zh--zh.clex", "zh--zh.cngm"}, "Wrong remote asset set")
    require(download(f"https://github.com/{repository}/releases/latest/download/manifest.json") == manifest_bytes,
            "latest/download returned a stale manifest")
    print(json.dumps({**check_payload(blobs, variant), "version": version,
                      "manifest_sha256": digest(manifest_bytes), "release_discovery": "PASS"},
                     ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify-release"))
    parser.add_argument("--variant", choices=MARKERS, default="B")
    parser.add_argument("--version", required=True)
    parser.add_argument("--repository", default=BASE_REPO)
    parser.add_argument("--stage", type=pathlib.Path)
    parser.add_argument("--expected-manifest", type=pathlib.Path)
    args = parser.parse_args()
    if args.command == "build":
        if args.stage is None:
            parser.error("--stage is required")
        build(args.stage.resolve(), args.repository, args.version, args.variant)
    else:
        verify_release(args.repository, args.version, args.variant, args.expected_manifest)


if __name__ == "__main__":
    main()
