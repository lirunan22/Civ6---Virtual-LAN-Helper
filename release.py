#!/usr/bin/env python3
"""Independent plugin release, with fixed, non-sensitive SSH-verifiable receipts."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

import build
from build import OUTPUT, VERSION

FLAGS = ("validation", "payload", "sourcePort", "replyToGame", "processSockets",
         "rawPayload", "rawSourcePort", "exclusiveGameReply", "gui", "inputValidation",
         "defaultUnprivileged", "bundledFiles", "universal", "signature", "helperValidation", "authorizationSyntax")
NAMES = (f"Civ6-Discovery-Helper-{VERSION}-mac-universal.zip",
         f"Civ6-Discovery-Helper-{VERSION}-source.zip", "SHA256SUMS.txt")


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


def context():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        raise RuntimeError("Invalid repository")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    return repo, sha


def publish_stage(value):
    (Path(os.environ["RUNNER_TEMP"]) / "civ6-plugin-publish-stage.json").write_text(json.dumps(value))


def publish(finalizing=False):
    repo, sha = context()
    tag = os.environ.get("PLUGIN_TAG", "")
    if tag != f"v{VERSION}":
        raise RuntimeError("Tag/version mismatch")
    publish_stage("context")
    tagged = subprocess.check_output(["git", "rev-parse", f"{tag}^{{commit}}"], text=True).strip()
    if finalizing:
        # Recovery changes publication code only. The uploaded app was built at
        # the original tag, and the same production sources must still match.
        subprocess.run(["git", "diff", "--exit-code", tag, "HEAD", "--",
                        "src", "build.py"],
                       check=True, stdout=subprocess.DEVNULL)
        sha = tagged
    elif tagged != sha:
        raise RuntimeError("Tag/checkout mismatch")
    publish_stage("visibility")
    if json.loads(gh("api", f"repos/{repo}"))["private"] is not False:
        raise RuntimeError("This project must be published in the user-approved public repository")
    publish_stage("checks")
    verification = json.loads((Path(os.environ["RUNNER_TEMP"]) / "civ6-plugin-check.json").read_text())
    if any(verification.get(flag) is not True for flag in FLAGS):
        raise RuntimeError("Native plugin verification incomplete")
    publish_stage("manifest")
    hashes = {name: hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest() for name in NAMES}
    expected = "".join(f"{hashes[name]}  {name}\n" for name in NAMES[:2])
    if (OUTPUT / "SHA256SUMS.txt").read_text() != expected:
        raise RuntimeError("Manifest mismatch")
    publish_stage("lookup")
    existing = subprocess.run(["gh", "release", "view", tag, "--repo", repo, "--json", "databaseId"],
                              text=True, capture_output=True)
    if existing.returncode:
        if finalizing:
            raise RuntimeError("Existing release not found")
        publish_stage("draft")
        gh("release", "create", tag, "--repo", repo, "--verify-tag", "--draft", "--latest=false",
           "--title", f"文明 VI · Mac 联机发现助手 {VERSION}",
           "--notes-file", "RELEASE_NOTES.md")
    release_id = json.loads(gh("release", "view", tag, "--repo", repo, "--json", "databaseId"))["databaseId"]
    if not isinstance(release_id, int) or release_id <= 0:
        raise RuntimeError("Invalid release ID")

    def inspect():
        data = json.loads(gh("api", f"repos/{repo}/releases/{release_id}"))
        if data["tag_name"] != tag:
            raise RuntimeError("Release mismatch")
        return data

    release = inspect()
    by_name = {asset["name"]: asset for asset in release["assets"]}
    if len(by_name) != len(release["assets"]) or any(name not in NAMES for name in by_name):
        raise RuntimeError("Unexpected existing assets")
    publish_stage("upload")
    for name in NAMES:
        if name in by_name:
            asset = by_name[name]
            if (asset["size"] != (OUTPUT / name).stat().st_size or
                    asset.get("digest") != "sha256:" + hashes[name] or asset.get("state") != "uploaded"):
                raise RuntimeError("Existing asset differs; it will not be overwritten")
        elif release["draft"] and not finalizing:
            gh("release", "upload", tag, str(OUTPUT / name), "--repo", repo)
        else:
            raise RuntimeError("Published release missing an asset; refusing to modify")
    publish_stage("verify-assets")
    for _ in range(20):
        release = inspect()
        if len(release["assets"]) == len(NAMES) and all(a.get("digest") for a in release["assets"]):
            break
        time.sleep(2)
    assert len(release["assets"]) == len(NAMES)
    for asset in release["assets"]:
        name = asset["name"]
        assert asset["state"] == "uploaded" and asset["size"] == (OUTPUT / name).stat().st_size
        assert asset.get("digest") == "sha256:" + hashes[name]
        # Draft URLs can use an untagged placeholder. Check the permanent URL
        # after publication, while size/digest must match before it is published.
    publish_stage("publish")
    if release["draft"]:
        gh("api", "--method", "PATCH", f"repos/{repo}/releases/{release_id}",
           "-F", "draft=false", "-f", "make_latest=true")
    publish_stage("verify-published")
    release = inspect()
    assert not release["draft"]
    for asset in release["assets"]:
        assert asset["name"] in NAMES
        assert asset["browser_download_url"] == f"https://github.com/{repo}/releases/download/{tag}/{asset['name']}"
    result = {"status": "success", "tag": tag, "commit": sha,
              "url": f"https://github.com/{repo}/releases/tag/{tag}",
              "assets": [{"name": a["name"], "size": a["size"], "digest": a["digest"],
                          "url": a["browser_download_url"]} for a in release["assets"]]}
    (Path(os.environ["RUNNER_TEMP"]) / "civ6-plugin-release.json").write_text(json.dumps(result))
    publish_stage("complete")


def finalize():
    """Recheck the original uploaded app, never rebuild/replace its assets."""
    repo, _ = context()
    tag = os.environ["PLUGIN_TAG"]
    if tag != f"v{VERSION}":
        raise RuntimeError("Invalid finalization tag")
    pins = json.loads(os.environ["PLUGIN_PIN_SHA256"])
    if set(pins) != set(NAMES) or any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in pins.values()):
        raise RuntimeError("Missing verified attachment pins")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        gh("release", "download", tag, "--repo", repo, "--dir", str(OUTPUT), "--pattern", name)
        if hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest() != pins[name]:
            raise RuntimeError("Existing attachment pin mismatch")
    with tempfile.TemporaryDirectory(prefix="civ6-recheck-") as temp:
        build.run("ditto", "-x", "-k", OUTPUT / NAMES[0], temp)
        app = Path(temp) / build.APP_NAME
        build.run("codesign", "--verify", "--deep", "--strict", app)
        for binary in (app / "Contents/MacOS/Civ6Discovery", app / "Contents/Helpers/civ6-sender"):
            for arch in ("arm64", "x86_64"):
                build.run("lipo", binary, "-verify_arch", arch)
        build.run("osadecompile", app / "Contents/Resources/authorize.scpt", capture_output=True)
        build.record("compiled", {"universal": True, "signature": True, "authorizationSyntax": True})
        build.verify(app)
        build.record("complete")
    publish(finalizing=True)


def receipt():
    repo, sha = context()
    temp = Path(os.environ["RUNNER_TEMP"])
    run_id, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
    if not run_id.isdigit() or not attempt.isdigit():
        raise RuntimeError("Invalid run context")
    tag = os.environ.get("PLUGIN_TAG", "")
    if tag and tag != f"v{VERSION}":
        raise RuntimeError("Invalid tag")
    result_path = temp / "civ6-plugin-release.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    check_path = temp / "civ6-plugin-check.json"
    checks = json.loads(check_path.read_text()) if check_path.exists() else {}
    success = os.environ.get("PLUGIN_OUTCOME") == "success" and all(checks.get(flag) is True for flag in FLAGS)
    if tag:
        success = success and result.get("status") == "success"
    # Fixed booleans and allowlisted local build metadata only; never logs, paths,
    # IPs, process names, AppleScript output, credentials, or exception messages.
    record = {"status": "success" if success else "failure", "commit": sha,
              "run": f"https://github.com/{repo}/actions/runs/{run_id}",
              "checks": {flag: checks.get(flag) is True for flag in FLAGS}}
    stages = ("compile-arm64", "compile-x86_64", "merge", "bundle", "authorization", "sign", "compiled", "network", "raw", "gui", "archive", "complete")
    record["stage"] = checks.get("stage") if checks.get("stage") in stages else "unknown"
    publish_path = temp / "civ6-plugin-publish-stage.json"
    phase = json.loads(publish_path.read_text()) if publish_path.exists() else "none"
    record["publishStage"] = phase if phase in ("context", "visibility", "checks", "manifest", "lookup", "draft", "upload", "verify-assets", "publish", "verify-published", "complete", "none") else "unknown"
    record["steps"] = {key: os.environ.get("STEP_" + key.upper(), "unknown")
                       for key in ("build", "publish")}
    record["steps"] = {key: value if value in ("success", "failure", "skipped", "cancelled") else "unknown"
                       for key, value in record["steps"].items()}
    if tag:
        record["tag"] = tag
        if result.get("status") == "success":
            record["commit"] = result["commit"]
            record["url"] = f"https://github.com/{repo}/releases/tag/{tag}"
            assets = result.get("assets", [])
            if len(assets) == 3 and {a.get("name") for a in assets} == set(NAMES):
                record["assets"] = [{"name": a["name"], "size": a["size"], "digest": a["digest"],
                                     "url": f"https://github.com/{repo}/releases/download/{tag}/{a['name']}"}
                                    for a in assets if isinstance(a.get("size"), int) and a["size"] > 0 and
                                    re.fullmatch(r"sha256:[0-9a-f]{64}", a.get("digest", ""))]
    marker = f"ci-status/{tag or 'native'}/{run_id}-{attempt}"
    obj = json.loads(gh("api", "--method", "POST", f"repos/{repo}/git/tags", "-f", f"tag={marker}",
                        "-f", f"message={json.dumps(record, separators=(',', ':'))}", "-f", f"object={sha}", "-f", "type=commit"))
    gh("api", "--method", "POST", f"repos/{repo}/git/refs", "-f", f"ref=refs/tags/{marker}", "-f", f"sha={obj['sha']}")


if __name__ == "__main__":
    if sys.argv[1:] == ["publish"]:
        publish()
    elif sys.argv[1:] == ["finalize"]:
        finalize()
    elif sys.argv[1:] == ["receipt"]:
        receipt()
    else:
        raise SystemExit("Usage: release.py publish|finalize|receipt")
