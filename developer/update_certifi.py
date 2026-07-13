#!/usr/bin/env python3

"""
Updates the bundled certifi module.

Run as "./update_certifi.py YYYY.MM.DD" to get a specific release from PyPI.
"""

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile


class Utilities:
    def download_wheel(self, version, dest_dir):
        """Download the certifi wheel from PyPI."""
        print(f"Downloading certifi {version}")
        subprocess.check_output(
            [
                "pip",
                "download",
                f"certifi=={version}",
                "--no-deps",
                "--index-url",
                "https://pypi.org/simple/",
                "-d",
                str(dest_dir),
            ]
        )

    def unzip_archive(self, file_path, temp_dir):
        """Unzip in a temp dir."""
        print(f"Unzipping {file_path.name}")
        subprocess.check_output(["unzip", str(file_path), "-d", str(temp_dir)])

    def remove_folder(self, path):
        """Remove a folder recursively."""
        print(f"Removing the folder {path}")
        shutil.rmtree(path, ignore_errors=True)

    def git_remove(self, target):
        print(f"Removing {target} in git.")
        try:
            subprocess.check_output(["git", "rm", "-rf"] + target)
        except Exception:
            pass

    def copy_folder(self, source, target):
        """Copy a folder recursively."""
        shutil.copytree(source, target)

    def update_requirements(self, req_file, version):
        """Update the certifi version pin in requirements.txt."""
        content = req_file.read_text()
        content = re.sub(r"certifi==[\d.]+", f"certifi=={version}", content)
        req_file.write_text(content)


def main(temp_path, repo_root, version):
    certifi_dir = repo_root / "shotgun_api3" / "lib" / "certifi"
    req_file = repo_root / "shotgun_api3" / "lib" / "requirements.txt"

    utilities = Utilities()

    # Download the wheel from PyPI
    utilities.download_wheel(version, temp_path)

    # Find the downloaded wheel file
    wheels = list(temp_path.glob("certifi-*.whl"))
    if not wheels:
        raise RuntimeError("No certifi wheel found after download")

    # Unzip into a temp dir
    unzipped = temp_path / "unzipped"
    unzipped.mkdir()
    utilities.unzip_archive(wheels[0], unzipped)

    # Remove old certifi from git and disk
    utilities.git_remove([str(certifi_dir)])
    utilities.remove_folder(certifi_dir)

    # Copy new certifi into place (only the certifi/ package, not .dist-info)
    print("Copying new version of certifi")
    utilities.copy_folder(str(unzipped / "certifi"), str(certifi_dir))

    # Update requirements.txt version pin
    print("Updating requirements.txt")
    utilities.update_requirements(req_file, version)

    # Stage changes
    print("Adding to git")
    subprocess.check_output(
        ["git", "add", str(certifi_dir), str(req_file)]
    )  # nosec B607


def find_repo_root():
    path = pathlib.Path(__file__).resolve()
    for parent in [path, *path.parents]:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Could not find repo root (no .git directory found)")


if __name__ == "__main__":
    try:
        temp_path = pathlib.Path(tempfile.mkdtemp())
        main(temp_path, find_repo_root(), sys.argv[1])
    finally:
        shutil.rmtree(temp_path)
