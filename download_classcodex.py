#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

# ============================ CONFIGURATION ============================
# Replace this path with your WoW Retail AddOns folder.
# Windows example:
# ADDONS_PATH = r"C:\Program Files (x86)\World of Warcraft\_retail_\Interface\AddOns"
# macOS/Linux example:
# ADDONS_PATH = "/path/World of Warcraft/_retail_/Interface/AddOns"
ADDONS_PATH = r"ENTER YOUR ADDON PATH"

# Parameters for Retail.
CDN_BASE_URL = "https://static.bigbrain.gg/wow/addons/class-codex"
GAME_VERSION_ID = "retail"
RELEASE_CHANNEL = "production"
DOWNLOAD_TIMEOUT_SECONDS = 60

# If True, only prints which files would be downloaded; does not modify any files.
DRY_RUN = False

# =======================================================================

CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".part")
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "ClassCodex-installer/1.0"}
        )
        with urllib.request.urlopen(
            request,
            timeout=DOWNLOAD_TIMEOUT_SECONDS
        ) as response, temp.open("wb") as out:
            shutil.copyfileobj(response, out, length=CHUNK_SIZE)
        os.replace(temp, destination)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def download_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ClassCodex-installer/1.0"}
    )
    with urllib.request.urlopen(
        request,
        timeout=DOWNLOAD_TIMEOUT_SECONDS
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def file_url(build_id: str, manifest_path: str) -> str:
    encoded_path = "/".join(
        urllib.parse.quote(part, safe="")
        for part in manifest_path.split("/")
    )
    return (
        f"{CDN_BASE_URL.rstrip('/')}/builds/"
        f"{GAME_VERSION_ID}/{build_id}/{encoded_path}"
    )


def main() -> int:
    addons_path_text = ADDONS_PATH.strip()

    if not addons_path_text or addons_path_text.startswith("/path/"):
        print(
            "Error: set the ADDONS_PATH value at the top of the file.",
            file=sys.stderr
        )
        return 2

    addons_path = Path(addons_path_text).expanduser().resolve()

    if not addons_path.is_dir():
        print(
            f"Error: AddOns folder not found: {addons_path}",
            file=sys.stderr
        )
        return 2

    config_url = (
        f"{CDN_BASE_URL.rstrip('/')}/channels/"
        f"{GAME_VERSION_ID}/{RELEASE_CHANNEL}/config.json"
    )

    print(f"Downloading configuration: {config_url}")
    config = download_json(config_url)

    if (
        config.get("gameVersionId") != GAME_VERSION_ID
        or config.get("channel") != RELEASE_CHANNEL
    ):
        print(
            "Error: the received configuration does not match "
            "the configured game version/channel.",
            file=sys.stderr
        )
        return 3

    build_id = config.get("buildId")
    manifest_url = config.get("manifestUrl")
    manifest_expected_hash = config.get("manifestSha256")

    if not all(
        isinstance(x, str) and x
        for x in (build_id, manifest_url, manifest_expected_hash)
    ):
        print(
            "Error: incomplete channel configuration.",
            file=sys.stderr
        )
        return 3

    print(f"Downloading manifest, build: {build_id}")

    with tempfile.TemporaryDirectory(prefix="classcodex-") as tempdir:
        manifest_path = Path(tempdir) / "manifest.json"
        download(manifest_url, manifest_path)

        if sha256_file(manifest_path) != manifest_expected_hash.lower():
            print(
                "Error: manifest SHA-256 verification failed.",
                file=sys.stderr
            )
            return 4

        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

    addon = manifest.get("addon", {})

    if (
        addon.get("id") != "class-codex"
        or addon.get("name") != "ClassCodex"
        or addon.get("gameVersionId") != GAME_VERSION_ID
    ):
        print(
            "Error: the manifest does not belong to the expected "
            "ClassCodex addon.",
            file=sys.stderr
        )
        return 4

    if manifest.get("build", {}).get("id") != build_id:
        print(
            "Error: the build ID in the configuration does not match "
            "the build ID in the manifest.",
            file=sys.stderr
        )
        return 4

    files = manifest.get("files")

    if not isinstance(files, list) or not files:
        print(
            "Error: the manifest does not contain any files.",
            file=sys.stderr
        )
        return 4

    downloaded = 0
    skipped = 0

    for entry in files:
        relative = entry.get("path")
        expected_size = entry.get("size")
        expected_hash = entry.get("sha256")

        if (
            not isinstance(relative, str)
            or not relative.startswith("ClassCodex/")
            or ".." in relative.split("/")
        ):
            print(
                f"Error: unsafe manifest path: {relative!r}",
                file=sys.stderr
            )
            return 4

        if not isinstance(expected_size, int) or not isinstance(
            expected_hash, str
        ):
            print(
                f"Error: invalid manifest entry: {relative!r}",
                file=sys.stderr
            )
            return 4

        target = addons_path.joinpath(*relative.split("/"))

        valid_local = (
            target.is_file()
            and target.stat().st_size == expected_size
            and sha256_file(target) == expected_hash.lower()
        )

        if valid_local:
            skipped += 1
            print(f"OK       {relative}")
            continue

        print(f"DOWNLOAD {relative}")

        if DRY_RUN:
            continue

        download(file_url(build_id, relative), target)

        if (
            target.stat().st_size != expected_size
            or sha256_file(target) != expected_hash.lower()
        ):
            target.unlink(missing_ok=True)
            print(
                f"Error: downloaded file verification failed: {relative}",
                file=sys.stderr
            )
            return 5

        downloaded += 1

    print(
        f"\nDone. Build: {build_id}; "
        f"downloaded: {downloaded}; already up to date: {skipped}."
    )
    print(f"Addon folder: {addons_path / 'ClassCodex'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
