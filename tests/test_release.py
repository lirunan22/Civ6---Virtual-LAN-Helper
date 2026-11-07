"""Check immutable release assets, correct tags, and filtered CI receipts."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("plugin_release", ROOT / "release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class PluginReleaseTests(unittest.TestCase):
    def test_draft_placeholder_urls_are_checked_after_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            import hashlib
            root = Path(temp)
            (root / "civ6-plugin-check.json").write_text(json.dumps({key: True for key in release.FLAGS}))
            for name in release.NAMES[:2]:
                (root / name).write_bytes(b"verified-app")
            (root / "SHA256SUMS.txt").write_text("".join(
                f"{hashlib.sha256((root/name).read_bytes()).hexdigest()}  {name}\n" for name in release.NAMES[:2]))
            draft = True
            calls = []

            def gh(*args):
                nonlocal draft
                calls.append(args)
                if args == ("api", "repos/owner/repo"):
                    return '{"private":false}'
                if args[:2] == ("release", "view"):
                    return '{"databaseId":1}'
                if args[:3] == ("api", "--method", "PATCH"):
                    self.assertIn("make_latest=true", args)
                    draft = False
                    return '{}'
                if args == ("api", "repos/owner/repo/releases/1"):
                    assets = [{"name": name, "size": (root/name).stat().st_size, "state": "uploaded",
                               "digest": "sha256:" + hashlib.sha256((root/name).read_bytes()).hexdigest(),
                               "browser_download_url": f"https://github.com/owner/repo/releases/download/{'untagged-placeholder' if draft else 'v' + release.VERSION}/{name}"}
                              for name in release.NAMES]
                    return json.dumps({"tag_name": f"v{release.VERSION}", "draft": draft, "assets": assets})
                self.fail("Unexpected publishing command")

            with patch.dict(os.environ, {"PLUGIN_TAG": f"v{release.VERSION}", "RUNNER_TEMP": temp}), \
                 patch.object(release, "OUTPUT", root), patch.object(release, "context", return_value=("owner/repo", "a"*40)), \
                 patch.object(release.subprocess, "check_output", return_value="a"*40), \
                 patch.object(release.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)), \
                 patch.object(release, "gh", side_effect=gh):
                release.publish()
            self.assertFalse(draft)
            self.assertEqual(json.loads((root / "civ6-plugin-release.json").read_text())["status"], "success")
            self.assertFalse(any(call[:2] == ("release", "upload") for call in calls))

    def test_existing_changed_asset_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "civ6-plugin-check.json").write_text(json.dumps({key: True for key in release.FLAGS}))
            import hashlib
            manifest = ""
            for name in release.NAMES[:2]:
                (root / name).write_bytes(b"new-build")
                manifest += f"{hashlib.sha256(b'new-build').hexdigest()}  {name}\n"
            (root / "SHA256SUMS.txt").write_text(manifest)
            calls = []

            def gh(*args):
                calls.append(args)
                if args == ("api", "repos/owner/repo"):
                    return '{"private":false}'
                if args[:2] == ("release", "view"):
                    return '{"databaseId":1}'
                if args == ("api", "repos/owner/repo/releases/1"):
                    return json.dumps({"tag_name": f"v{release.VERSION}", "draft": False,
                                       "assets": [{"name": release.NAMES[0], "size": 9,
                                                   "digest": "sha256:" + "0" * 64, "state": "uploaded"}]})
                self.fail("Unexpected publishing command")

            with patch.dict(os.environ, {"PLUGIN_TAG": f"v{release.VERSION}", "RUNNER_TEMP": temp}), \
                 patch.object(release, "OUTPUT", root), patch.object(release, "context", return_value=("owner/repo", "a" * 40)), \
                 patch.object(release.subprocess, "check_output", return_value="a" * 40), \
                 patch.object(release.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)), \
                 patch.object(release, "gh", side_effect=gh):
                with self.assertRaisesRegex(RuntimeError, "not be overwritten"):
                    release.publish()
            self.assertFalse(any(call[:2] in (("release", "upload"), ("release", "edit")) for call in calls))

    def test_mismatched_tag_is_rejected_before_upload(self):
        with patch.dict(os.environ, {"PLUGIN_TAG": "v0.14.1"}), \
             patch.object(release, "context", return_value=("owner/repo", "a" * 40)), \
             patch.object(release, "gh") as gh:
            with self.assertRaisesRegex(RuntimeError, "Tag/version"):
                release.publish()
            gh.assert_not_called()

    def test_failure_receipt_does_not_include_local_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            data = {key: True for key in release.FLAGS}
            data.update({"gui": False, "stage": "gui", "ip": "sensitive-local-ip", "stderr": "must-stay-local"})
            (Path(temp) / "civ6-plugin-check.json").write_text(json.dumps(data))
            calls = []

            def gh(*args):
                calls.append(args)
                return '{"sha":"' + "b" * 40 + '"}'

            with patch.dict(os.environ, {"PLUGIN_TAG": "", "RUNNER_TEMP": temp, "GITHUB_RUN_ID": "123",
                                        "GITHUB_RUN_ATTEMPT": "1", "PLUGIN_OUTCOME": "failure"}), \
                 patch.object(release, "context", return_value=("owner/repo", "a" * 40)), \
                 patch.object(release, "gh", side_effect=gh):
                release.receipt()
            body = next(arg[len("message="):] for arg in calls[0] if arg.startswith("message="))
            result = json.loads(body)
            self.assertEqual(result["status"], "failure")
            self.assertEqual(result["stage"], "gui")
            self.assertNotIn("sensitive-local-ip", body)
            self.assertNotIn("must-stay-local", body)
            self.assertFalse(result["checks"]["gui"])


if __name__ == "__main__":
    unittest.main()
