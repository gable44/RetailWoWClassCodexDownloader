# WoW ClassCodex Addon Downloader

This repository provides a downloader script for the ClassCodex Addon for World of Warcraft.

# ClassCodex Downloader

A simple downloader script for the [ClassCodex](https://addons.wago.io/addons/classcodex) Addon for World of Warcraft. (https://www.icy-veins.com/download)

The script downloads the latest production build of ClassCodex, verifies the downloaded files using SHA-256 checksums, and installs or updates the addon in your addons folder defined in the script folder.

## Features

* Downloads the latest ClassCodex production build
* Verifies the manifest using SHA-256
* Verifies every downloaded file using SHA-256
* Skips files that are already up to date
* Prevents unsafe manifest paths
* Uses temporary files during downloads to avoid incomplete files
* Detects the World of Warcraft installation automatically
* Prompts for the WoW installation folder when automatic detection fails
* Highlights and confirms the selected AddOns folder
* Shows installed and available versions before updating
* Requires confirmation before installing or updating files
* Supports a dry-run mode

## Requirements

* Python 3.9 or newer
* World of Warcraft game client

The script uses only Python's standard library, so no additional packages are required.

## Usage
Run the script from a terminal:
```bash
python download_classcodex.py
```

The downloader looks for World of Warcraft in registered and standard installation
locations. If it cannot find the game, enter the top-level `World of Warcraft`
folder when prompted. Do not enter the `AddOns` folder; the downloader derives
`_retail_/Interface/AddOns` automatically.

For a custom or portable installation, you can optionally set the
`WOW_INSTALL_PATH` environment variable to the top-level `World of Warcraft`
folder.

After selecting the folder, the downloader asks you to confirm it. It then
downloads and verifies the release manifest, compares the installed files with
the available build, and displays the installed version, available version,
build ID, and number of files requiring an update. The installation or update
starts only after a second confirmation. Choosing no does not change addon files.

## Dry Run
If you want to see which files would be downloaded without modifying anything, set:
```python
DRY_RUN = True
```

The script will:
1. Detect or ask for the WoW folder and confirm the highlighted destination.
2. Download the current ClassCodex channel configuration.
3. Download and verify the manifest.
4. Verify that the manifest belongs to ClassCodex Retail.
5. Compare the installed version and files with the available build.
6. Ask before starting an installation or update.
7. Download and verify missing or outdated files.
8. Report the installed build and download results.



## Security
The downloader performs integrity checks before installing files.
The channel configuration provides the expected SHA-256 hash of the manifest. The manifest then provides the expected SHA-256 hash and file size for each addon file.
Downloaded files are verified before they are considered successfully installed.
The script also rejects manifest paths containing unsafe path traversal components.

## Disclaimer
This is an independent downloader script for the ClassCodex Addon.
World of Warcraft and related trademarks are property of their respective owners. This project is not affiliated with or endorsed by Blizzard Entertainment unless explicitly stated otherwise.
The ClassCodex addon, its data, and its distribution infrastructure may be subject to their own licenses and terms. This repository's license applies only to the code contained in this repository.
