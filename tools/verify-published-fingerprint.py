#!/usr/bin/env python3
"""Verify the immutable published Clink zh IME fingerprint release."""

import hashlib
import json
import struct
import urllib.request


TAG = "vzh-ime-fingerprint-1-1"
BASE_URL = (
    "https://github.com/dayifulalala-del/clink-language-packs/releases/download/"
    f"{TAG}"
)
EXPECTED = {
    "zh.cime": {
        "asset": "zh--zh.cime",
        "byteCount": 63,
        "sha256": "5e05b6b2a026435b3807db8c99884626f74b6619b6dcf0336286f465e29f2500",
    },
    "zh.clex": {
        "asset": "zh--zh.clex",
        "byteCount": 98,
        "sha256": "4f985c2b10388f06fd12af2b595beca310ee7668329119a20405e62a439749f9",
    },
}
EXPECTED_IME_ROWS = {
    "pin": ["万象"],
    "yin": ["验证"],
    "pinyin": ["万象验证"],
    "pin yin": ["万象验证"],
}


def download(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "clink-zh-fingerprint-verifier/1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main():
    manifest_data = download(f"{BASE_URL}/manifest.json")
    manifest = json.loads(manifest_data)
    assert manifest["version"] == TAG, manifest["version"]
    assert len(manifest["packs"]) == 1, manifest["packs"]

    pack = manifest["packs"][0]
    assert pack["code"] == "zh", pack["code"]
    assert pack["version"] == TAG, pack["version"]
    assert [item["path"] for item in pack["assets"]] == [
        "zh.cime",
        "zh.clex",
    ], pack["assets"]

    downloaded = {}
    for item in pack["assets"]:
        expected = EXPECTED[item["path"]]
        assert item["url"] == f"{BASE_URL}/{expected['asset']}", item["url"]
        assert item["byteCount"] == expected["byteCount"], item
        assert item["sha256"] == expected["sha256"], item

        data = download(item["url"])
        digest = hashlib.sha256(data).hexdigest()
        assert len(data) == item["byteCount"], (item["path"], len(data))
        assert digest == item["sha256"], (item["path"], digest)
        downloaded[item["path"]] = data
        print(f"OK {item['path']}: {len(data)} bytes, sha256={digest}")

    rows = {}
    for raw in downloaded["zh.cime"].decode("utf-8").splitlines():
        fields = raw.split("\t")
        rows[fields[0]] = fields[1:]
    assert rows == EXPECTED_IME_ROWS, rows
    print("OK zh.cime: exact four fingerprint rows")

    clex = downloaded["zh.clex"]
    assert clex[:4] == b"CLEX", clex[:4]
    assert struct.unpack_from("<I", clex, 4)[0] == 1
    assert all(word.encode("utf-8") in clex for word in ("万象", "验证", "万象验证"))
    print("OK zh.clex: CLEX v1 with all three fingerprint entries")
    print(f"PASS: published fingerprint release {TAG} is internally consistent")


if __name__ == "__main__":
    main()
