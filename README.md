# WoW ClassCodex Retail Addon Downloader

This repository provides a downloader script for the ClassCodex Addon for World of Warcraft Retail version.

# ClassCodex Downloader

A simple downloader script for the [ClassCodex](https://addons.wago.io/addons/classcodex) Addon for World of Warcraft. (https://www.icy-veins.com/download)

The script downloads the latest production build of ClassCodex, verifies the downloaded files using SHA-256 checksums, and installs or updates the addon in your addons folder defined in the script folder.

Looking for the Forever version? https://github.com/gable44/ForeverWoWClassCodexDownloader

## Features

* Downloads the latest ClassCodex production build
* Verifies the manifest using SHA-256
* Verifies every downloaded file using SHA-256
* Skips files that are already up to date
* Prevents unsafe manifest paths
* Uses temporary files during downloads to avoid incomplete files
* Supports a dry-run mode

## Requirements

* Python 3.9 or newer
* World of Warcraft Retail game client

The script uses only Python's standard library, so no additional packages are required.

## Configuration

Open `download_classcodex-retail.py` and set `ADDONS_PATH` to your World of Warcraft `AddOns` folder.

## Usage
Run the script from a terminal:
```bash
python download_classcodex-retail.py
```

## Dry Run
If you want to see which files would be downloaded without modifying anything, set:
```python
DRY_RUN = True
```

The script will:
1. Download the current ClassCodex channel configuration.
2. Download and verify the manifest.
3. Verify that the manifest belongs to ClassCodex Retail.
4. Compare local files with the expected SHA-256 hashes.
5. Download missing or outdated files.
6. Verify every downloaded file.
7. Report the installed build and download results.



## Security
The downloader performs integrity checks before installing files.
The channel configuration provides the expected SHA-256 hash of the manifest. The manifest then provides the expected SHA-256 hash and file size for each addon file.
Downloaded files are verified before they are considered successfully installed.
The script also rejects manifest paths containing unsafe path traversal components.

## Disclaimer
This is an independent downloader script for the ClassCodex Addon.
World of Warcraft and related trademarks are property of their respective owners. This project is not affiliated with or endorsed by Blizzard Entertainment unless explicitly stated otherwise.
The ClassCodex addon, its data, and its distribution infrastructure may be subject to their own licenses and terms. This repository's license applies only to the code contained in this repository.
