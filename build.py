#!/usr/bin/env python3
"""Build a standalone, universal macOS app; no Python runtime is shipped."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
VERSION = "0.1.1"
APP_NAME = "Civ6 Discovery Helper.app"
OUTPUT = ROOT / "artifacts"


def record(stage, values=None):
    file = Path(os.environ.get("RUNNER_TEMP", OUTPUT)) / "civ6-plugin-check.json"
    file.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(file.read_text()) if file.exists() else {}
    data.update(values or {})
    data["stage"] = stage
    file.write_text(json.dumps(data, indent=2) + "\n")


def run(*args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def build():
    if platform.system() != "Darwin":
        raise SystemExit("macOS/Xcode Command Line Tools are required; use the private GitHub build.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = OUTPUT / APP_NAME
    if app.exists():
        shutil.rmtree(app)
    binary = app / "Contents" / "MacOS"
    helper = app / "Contents" / "Helpers"
    resources = app / "Contents" / "Resources"
    for folder in (binary, helper, resources):
        folder.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="civ6-build-") as temp:
        temp = Path(temp)
        for arch in ("arm64", "x86_64"):
            record("compile-" + arch)
            common = ["xcrun", "clang", "-arch", arch, "-mmacosx-version-min=12.0", "-O2", "-Wall", "-Wextra", "-I", ROOT / "src"]
            run(*common, "-c", ROOT / "src/discovery.c", "-o", temp / f"core-{arch}.o")
            run(*common, "-fobjc-arc", ROOT / "src/main.m", temp / f"core-{arch}.o",
                "-framework", "Cocoa", "-lproc", "-o", temp / f"gui-{arch}")
            run(*common, ROOT / "src/helper.c", temp / f"core-{arch}.o", "-lproc", "-o", temp / f"sender-{arch}")
        record("merge")
        for name, destination in (("gui", binary / "Civ6Discovery"), ("sender", helper / "civ6-sender")):
            run("lipo", "-create", *(temp / f"{name}-{arch}" for arch in ("arm64", "x86_64")), "-output", destination)
            for arch in ("arm64", "x86_64"):
                run("lipo", destination, "-verify_arch", arch)
    record("bundle")
    info = {
        "CFBundleExecutable": "Civ6Discovery", "CFBundleIdentifier": "local.deskcompanion.civ6-discovery",
        "CFBundleName": "Civ6 Discovery Helper", "CFBundleDisplayName": "文明 VI 联机发现助手",
        "CFBundlePackageType": "APPL", "CFBundleShortVersionString": VERSION, "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "12.0", "NSHighResolutionCapable": True,
        "NSLocalNetworkUsageDescription": "向你指定的文明 VI 房主补发局域网发现请求，以便游戏显示房间。",
        "NSSupportsAutomaticTermination": False,
    }
    (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps(info))
    for source, name in ((ROOT / "README.md", "使用说明.md"), (ROOT / "LICENSE.upstream", "LICENSE.upstream"),
                         (ROOT / "THIRD_PARTY.md", "THIRD_PARTY.md"), (ROOT / "LICENSE", "LICENSE"),
                         (ROOT / "VALIDATION.md", "VALIDATION.md")):
        shutil.copy2(source, resources / name)
    shutil.copytree(ROOT / "docs", resources / "docs")
    record("authorization")
    run("osacompile", "-o", resources / "authorize.scpt", ROOT / "src/authorize.applescript")
    record("authorization", {"authorizationSyntax": True})
    record("sign")
    run("codesign", "--force", "--sign", "-", helper / "civ6-sender")
    run("codesign", "--force", "--sign", "-", app)
    run("codesign", "--verify", "--deep", "--strict", app)
    record("compiled", {"universal": True, "signature": True})
    return app


def verify(app):
    results = {}
    with tempfile.TemporaryDirectory(prefix="civ6-check-") as temp:
        executable = Path(temp) / "Civ6_Exe_Child"
        run("xcrun", "clang", "-mmacosx-version-min=12.0", "-Wall", "-Wextra", "-I", ROOT / "src",
            ROOT / "tests/network.c", ROOT / "src/discovery.c", "-lproc", "-o", executable)
        record("network")
        results.update(json.loads(run(executable, capture_output=True, text=True).stdout))
        record("raw", results)
        # Disposable macOS runner: only loopback sockets, no external targets.
        results.update(json.loads(run("sudo", "-n", executable, "--raw", capture_output=True, text=True).stdout))
        record("gui", results)
    results.update(json.loads(run(app / "Contents/MacOS/Civ6Discovery", "--smoke-test", capture_output=True, text=True, timeout=30).stdout))
    assert all(value is True for value in results.values()), results
    results["universal"] = True
    results["signature"] = True
    record("archive", results)
    print(json.dumps(results))


def package(app):
    name = f"Civ6-Discovery-Helper-{VERSION}-mac-universal.zip"
    target = OUTPUT / name
    target.unlink(missing_ok=True)
    run("ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", app, target)
    source = OUTPUT / f"Civ6-Discovery-Helper-{VERSION}-source.zip"
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(ROOT.rglob("*")):
            if file.is_file() and "__pycache__" not in file.parts and file.relative_to(ROOT).parts[0] in {"src", "tests", "docs", ".github", "README.md", "LICENSE", "LICENSE.upstream", "THIRD_PARTY.md", "RELEASE_NOTES.md", "build.py", "release.py", "VALIDATION.md"}:
                archive.write(file, Path("civ6-mac-lan-helper") / file.relative_to(ROOT))
    # Validate the archived app, rather than just the build folder.
    with tempfile.TemporaryDirectory(prefix="civ6-archive-") as temp:
        run("ditto", "-x", "-k", target, temp)
        restored = Path(temp) / APP_NAME
        run("codesign", "--verify", "--deep", "--strict", restored)
        for executable in (restored / "Contents/MacOS/Civ6Discovery", restored / "Contents/Helpers/civ6-sender"):
            for arch in ("arm64", "x86_64"):
                run("lipo", executable, "-verify_arch", arch)
    names = (target, source)
    (OUTPUT / "SHA256SUMS.txt").write_text("".join(f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.name}\n" for file in names))
    record("complete")
    return names


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    built = build()
    if args.test:
        verify(built)
    package(built)
