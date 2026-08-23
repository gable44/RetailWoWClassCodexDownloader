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
from typing import Iterable, Optional

# ============================ CONFIGURATION ============================
# Parameters for Retail.
CDN_BASE_URL = "https://wow-class-codex.s3.us-east-1.amazonaws.com"
GAME_VERSION_ID = "retail"
RELEASE_CHANNEL = "production"
DOWNLOAD_TIMEOUT_SECONDS = 60

# If True, only prints which files would be downloaded; does not modify any files.
DRY_RUN = False

# =======================================================================

CHUNK_SIZE = 1024 * 1024
RETAIL_ADDONS_RELATIVE_PATH = Path("_retail_") / "Interface" / "AddOns"
ADDON_DIRECTORY_NAME = "ClassCodex"
ADDON_TOC_NAME = "ClassCodex.toc"


def addons_path_from_wow_root(wow_root: Path) -> Optional[Path]:
    """Return Retail's AddOns folder when wow_root is a valid WoW folder."""
    addons_path = wow_root.expanduser() / RETAIL_ADDONS_RELATIVE_PATH
    if addons_path.is_dir():
        return addons_path.resolve()
    return None


def windows_registry_wow_roots() -> Iterable[Path]:
    """Yield WoW install locations recorded by Blizzard on Windows."""
    if sys.platform != "win32":
        return

    try:
        import winreg
    except ImportError:
        return

    registry_keys = (
        r"SOFTWARE\Blizzard Entertainment\World of Warcraft",
        r"SOFTWARE\WOW6432Node\Blizzard Entertainment\World of Warcraft",
    )
    value_names = ("InstallPath", "GamePath")

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for key_name in registry_keys:
            try:
                with winreg.OpenKey(hive, key_name) as key:
                    for value_name in value_names:
                        try:
                            value, _ = winreg.QueryValueEx(key, value_name)
                        except OSError:
                            continue
                        if not isinstance(value, str) or not value.strip():
                            continue

                        path = Path(os.path.expandvars(value.strip().strip('"')))
                        if path.suffix.lower() == ".exe":
                            path = path.parent
                        if path.name.lower() == "_retail_":
                            path = path.parent
                        yield path
            except OSError:
                continue


def common_wow_roots() -> Iterable[Path]:
    """Yield likely WoW installation roots for the current platform."""
    env_path = os.environ.get("WOW_INSTALL_PATH")
    if env_path:
        yield Path(os.path.expandvars(env_path.strip().strip('"'))).expanduser()

    if sys.platform == "win32":
        yield from windows_registry_wow_roots()

        program_dirs = (
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
        )
        for directory in program_dirs:
            if directory:
                yield Path(directory) / "World of Warcraft"

        for drive_letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = Path(f"{drive_letter}:\\")
            yield drive / "World of Warcraft"
            yield drive / "Games" / "World of Warcraft"
    elif sys.platform == "darwin":
        yield Path("/Applications/World of Warcraft")
        yield Path.home() / "Applications" / "World of Warcraft"
    else:
        # Common Wine and Lutris locations.
        home = Path.home()
        yield home / ".wine/drive_c/Program Files (x86)/World of Warcraft"
        yield home / ".wine/drive_c/Program Files/World of Warcraft"
        lutris_drive = home / "Games" / "world-of-warcraft" / "drive_c"
        yield lutris_drive / "Program Files (x86)" / "World of Warcraft"
        yield lutris_drive / "Program Files" / "World of Warcraft"


def detect_addons_path(
    wow_roots: Optional[Iterable[Path]] = None,
) -> Optional[Path]:
    """Find the first valid Retail AddOns folder in known WoW roots."""
    seen = set()
    for wow_root in wow_roots if wow_roots is not None else common_wow_roots():
        key = os.path.normcase(os.path.abspath(str(wow_root)))
        if key in seen:
            continue
        seen.add(key)

        addons_path = addons_path_from_wow_root(wow_root)
        if addons_path is not None:
            return addons_path
    return None


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    """Ask a yes/no question and return False if input is cancelled."""
    choices = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = input(f"{prompt} {choices}: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.", file=sys.stderr)
            return False

        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer yes or no.")


def highlight_addons_path(addons_path: Path) -> None:
    """Make the selected destination easy to notice in every terminal."""
    border = "=" * 72
    print(f"\n{border}")
    print("SELECTED ADDONS FOLDER")
    print(f">>> {addons_path} <<<")
    print(border)


def prompt_for_addons_path() -> Optional[Path]:
    """Ask for the WoW root until it is valid or input is cancelled."""
    print(
        "Enter the World of Warcraft folder (not the AddOns folder).\n"
        "Example: C:\\Program Files (x86)\\World of Warcraft"
    )

    while True:
        try:
            value = input("World of Warcraft folder: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nPath entry cancelled.", file=sys.stderr)
            return None

        if not value:
            print("Please enter a folder, or press Ctrl+C to cancel.")
            continue

        wow_root = Path(
            os.path.expandvars(value.strip().strip('"').strip("'"))
        ).expanduser()
        addons_path = addons_path_from_wow_root(wow_root)
        if addons_path is not None:
            return addons_path

        print(
            "Retail AddOns folder not found below that folder. Expected:\n"
            f"  {wow_root / RETAIL_ADDONS_RELATIVE_PATH}"
        )


def resolve_addons_path() -> Optional[Path]:
    addons_path = detect_addons_path()
    if addons_path is not None:
        print("Detected the World of Warcraft installation automatically.")
        highlight_addons_path(addons_path)
        if ask_yes_no("Continue with this folder?", default=True):
            return addons_path
        print("Choose the correct World of Warcraft folder instead.")
    else:
        print("Could not detect the World of Warcraft installation automatically.")

    addons_path = prompt_for_addons_path()
    if addons_path is None:
        return None

    highlight_addons_path(addons_path)
    if ask_yes_no("Continue with this folder?", default=True):
        return addons_path

    print("Folder selection cancelled; no files were changed.")
    return None


def read_installed_version(addons_path: Path) -> Optional[str]:
    """Read the addon's human-facing version from its TOC metadata."""
    toc_path = addons_path / ADDON_DIRECTORY_NAME / ADDON_TOC_NAME
    try:
        lines = toc_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return None

    for line in lines:
        key, separator, value = line.partition(":")
        if separator and key.strip().lower() == "## version":
            version = value.strip()
            return version or None
    return None


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
    addons_path = resolve_addons_path()
    if addons_path is None:
        print(
            "Error: a valid World of Warcraft folder is required.",
            file=sys.stderr,
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

    if not isinstance(manifest, dict):
        print("Error: invalid manifest document.", file=sys.stderr)
        return 4

    addon = manifest.get("addon", {})

    if (
        not isinstance(addon, dict)
        or addon.get("id") != "class-codex"
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

    validated_files = []

    for entry in files:
        if not isinstance(entry, dict):
            print("Error: invalid manifest file entry.", file=sys.stderr)
            return 4

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

        validated_files.append(
            (
                relative,
                expected_size,
                expected_hash.lower(),
                addons_path.joinpath(*relative.split("/")),
            )
        )

    files_to_download = []
    for relative, expected_size, expected_hash, target in validated_files:
        valid_local = False
        try:
            valid_local = (
                target.is_file()
                and target.stat().st_size == expected_size
                and sha256_file(target) == expected_hash
            )
        except OSError:
            valid_local = False

        if not valid_local:
            files_to_download.append(
                (relative, expected_size, expected_hash, target)
            )

    installed_version = read_installed_version(addons_path)
    available_version = addon.get("tocVersion")
    if not isinstance(available_version, str) or not available_version:
        available_version = "unknown"

    print("\nVersion check")
    print("-------------")
    print(f"Installed version: {installed_version or 'not installed'}")
    print(f"Available version: {available_version}")
    print(f"Available build:   {build_id}")
    print(f"Files to update:   {len(files_to_download)}")
    print(f"Files up to date:  {len(validated_files) - len(files_to_download)}")

    if not files_to_download:
        print("\nClassCodex is already up to date; no files were changed.")
        return 0

    if DRY_RUN:
        print("\nDry run: these files would be downloaded:")
        for relative, _, _, _ in files_to_download:
            print(f"DOWNLOAD {relative}")
        print("\nDry run complete; no files were changed.")
        return 0

    action = "upgrade" if installed_version else "installation"
    if not ask_yes_no(f"Start the ClassCodex {action}?", default=False):
        print("Update cancelled; no files were changed.")
        return 0

    downloaded = 0

    for relative, expected_size, expected_hash, target in files_to_download:
        print(f"DOWNLOAD {relative}")

        download(file_url(build_id, relative), target)

        if (
            target.stat().st_size != expected_size
            or sha256_file(target) != expected_hash
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
        f"downloaded: {downloaded}; "
        f"already up to date: {len(validated_files) - downloaded}."
    )
    print(f"Addon folder: {addons_path / ADDON_DIRECTORY_NAME}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
