import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import download_classcodex


class AddonsPathTests(unittest.TestCase):
    def make_wow_install(self, parent: Path, name: str = "World of Warcraft") -> Path:
        wow_root = parent / name
        (wow_root / "_retail_" / "Interface" / "AddOns").mkdir(parents=True)
        return wow_root

    def test_addons_path_is_derived_from_wow_root(self):
        with tempfile.TemporaryDirectory() as tempdir:
            wow_root = self.make_wow_install(Path(tempdir))

            result = download_classcodex.addons_path_from_wow_root(wow_root)

            self.assertEqual(
                result,
                (wow_root / "_retail_" / "Interface" / "AddOns").resolve(),
            )

    def test_detection_skips_invalid_candidate(self):
        with tempfile.TemporaryDirectory() as tempdir:
            parent = Path(tempdir)
            wow_root = self.make_wow_install(parent, "valid")

            result = download_classcodex.detect_addons_path(
                [parent / "missing", wow_root]
            )

            self.assertEqual(
                result,
                (wow_root / "_retail_" / "Interface" / "AddOns").resolve(),
            )

    def test_prompt_accepts_top_level_wow_folder(self):
        with tempfile.TemporaryDirectory() as tempdir:
            wow_root = self.make_wow_install(Path(tempdir))
            with patch("builtins.input", return_value=f'"{wow_root}"'):
                result = download_classcodex.prompt_for_addons_path()

            self.assertEqual(
                result,
                (wow_root / "_retail_" / "Interface" / "AddOns").resolve(),
            )

    def test_invalid_wow_root_returns_none(self):
        with tempfile.TemporaryDirectory() as tempdir:
            self.assertIsNone(
                download_classcodex.addons_path_from_wow_root(Path(tempdir))
            )

    def test_read_installed_version_from_toc(self):
        with tempfile.TemporaryDirectory() as tempdir:
            addons_path = Path(tempdir)
            addon_path = addons_path / "ClassCodex"
            addon_path.mkdir()
            (addon_path / "ClassCodex.toc").write_text(
                "## Interface: 120100\n## Version: 1.2.3\n",
                encoding="utf-8",
            )

            self.assertEqual(
                download_classcodex.read_installed_version(addons_path),
                "1.2.3",
            )

    def test_yes_no_defaults_to_no_for_update_confirmation(self):
        with patch("builtins.input", return_value=""):
            self.assertFalse(download_classcodex.ask_yes_no("Start update?"))

    def test_yes_no_accepts_yes(self):
        with patch("builtins.input", return_value="yes"):
            self.assertTrue(download_classcodex.ask_yes_no("Continue?"))

    def test_declining_update_does_not_download_addon_files(self):
        with tempfile.TemporaryDirectory() as tempdir:
            addons_path = Path(tempdir)
            addon_path = addons_path / "ClassCodex"
            addon_path.mkdir()
            (addon_path / "ClassCodex.toc").write_text(
                "## Version: 1.0.0\n",
                encoding="utf-8",
            )

            payload = b"new addon data"
            manifest = {
                "addon": {
                    "id": "class-codex",
                    "name": "ClassCodex",
                    "gameVersionId": "retail",
                    "tocVersion": "2.0.0",
                },
                "build": {"id": "test-build"},
                "files": [
                    {
                        "path": "ClassCodex/payload.lua",
                        "size": len(payload),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    }
                ],
            }
            manifest_bytes = json.dumps(manifest).encode("utf-8")
            config = {
                "gameVersionId": "retail",
                "channel": "production",
                "buildId": "test-build",
                "manifestUrl": "https://example.invalid/manifest.json",
                "manifestSha256": hashlib.sha256(manifest_bytes).hexdigest(),
            }
            download_calls = []

            def fake_download(url, destination):
                download_calls.append(url)
                destination.write_bytes(manifest_bytes)

            with (
                patch(
                    "download_classcodex.resolve_addons_path",
                    return_value=addons_path,
                ),
                patch("download_classcodex.download_json", return_value=config),
                patch("download_classcodex.download", side_effect=fake_download),
                patch("download_classcodex.ask_yes_no", return_value=False),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                result = download_classcodex.main()

            self.assertEqual(result, 0)
            self.assertEqual(download_calls, [config["manifestUrl"]])
            self.assertFalse((addon_path / "payload.lua").exists())


if __name__ == "__main__":
    unittest.main()
