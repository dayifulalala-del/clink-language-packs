"""Small offline negative tests for the probe's safety checks."""
import copy
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest

import zh_ime_probe as probe
import rime_to_clink


class ProbeTests(unittest.TestCase):
    def test_pin_only_and_spaced_key_untouched(self):
        source = "pin\t品\t拼\npin yin\t拼音\npinyin\t拼音\nyin\t音\n".encode()
        a = probe.patch_pin(source, "A")
        b = probe.patch_pin(source, "B")
        self.assertEqual(b.replace("pin\t榀".encode(), "pin\t拼".encode()), a)
        self.assertEqual(probe.decode_cime(b)["pin yin"], ["拼音"])

    def test_reject_invalid_cime(self):
        for data in (b"pin\tx\npin\ty\n", b"z\tx\na\ty\n", b"pin\tx\tx\n",
                     b"pin\t\n", b"pin\tx\r\n", b"pin\t" + b"\t".join(str(i).encode() for i in range(17)) + b"\n"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                probe.decode_cime(data)

    def test_reject_out_of_range_word_id_and_truncated_cngm(self):
        bad_id = b"CNGM" + struct.pack("<IIII", 1, 1, 0, 5) + bytes([1])
        with self.assertRaises(ValueError):
            probe.check_cngm(bad_id, 5)
        with self.assertRaises(ValueError):
            probe.check_cngm(bad_id[:-1], 6)

    def test_manifest_strict_source_and_asset_set(self):
        blobs = {ext: ext.encode() for ext in probe.BASE}
        manifest = {"version": "test", "packs": [{"code": "zh", "version": "test", "assets": [
            {"path": f"zh.{ext}", "url": f"https://github.com/a/b/releases/download/test/zh--zh.{ext}",
             "sha256": probe.digest(data), "byteCount": len(data)} for ext, data in blobs.items()]}]}
        probe.check_manifest(manifest, "a/b", "test", blobs)
        for field, value in (("url", "https://example.com/old.cime"), ("byteCount", 0), ("sha256", "bad")):
            bad = copy.deepcopy(manifest)
            bad["packs"][0]["assets"][0][field] = value
            with self.assertRaises(ValueError):
                probe.check_manifest(bad, "a/b", "test", blobs)
        manifest["packs"][0]["code"] = "zh_wx"
        with self.assertRaises(ValueError):
            probe.check_manifest(manifest, "a/b", "test", blobs)

    def test_v1_missing_and_empty_inputs_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit):
                list(rime_to_clink.iter_input_files([pathlib.Path(directory) / "chengyu.dict.yaml"]))
            with self.assertRaises(SystemExit):
                list(rime_to_clink.iter_input_files([pathlib.Path(directory)]))

    def test_v2_missing_input_fails_without_outputs(self):
        script = pathlib.Path(__file__).with_name("build_zh_wanxiang_v2.py").resolve()
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(script), "missing.dict.yaml"],
                                    cwd=directory, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Required input not found", result.stderr)
            self.assertEqual(list(pathlib.Path(directory).iterdir()), [])

    def test_existing_stage_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                probe.build(pathlib.Path(directory), "a/b", "test", "B")


if __name__ == "__main__":
    unittest.main()
