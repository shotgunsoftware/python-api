#!/usr/bin/env python3

"""
Updates the httplib2 module.

Run as "./upgrade_httplib2.py vX.Y.Z" to get a specific release from github.
"""

import pathlib
import tempfile
import shutil
import subprocess
import sys


class Utilities:
    def download_archive(self, file_path, file_name):
        """Download the archive from github."""
        print(f"Downloading {file_name}")
        subprocess.check_output(
            [
                "curl",
                "-L",
                f"https://github.com/httplib2/httplib2/archive/{file_name}",
                "-o",
                file_path,
            ]
        )

    def unzip_archive(self, file_path, file_name, temp_dir):
        """Unzip in a temp dir."""
        print(f"Unzipping {file_name}")
        subprocess.check_output(["unzip", str(file_path), "-d", str(temp_dir)])

    def remove_folder(self, path):
        """Remove a folder recursively."""
        print(f"Removing the folder {path}")
        shutil.rmtree(path, ignore_errors=True)

    def git_remove(self, target):
        print(f"Removing {target} in git.")
        try:
            subprocess.check_output(
                [
                    "git",
                    "rm",
                    "-rf",
                ]
                + target
            )
        except Exception as e:
            pass

    def copy_folder(self, source, target):
        """Copy a folder recursively."""
        shutil.copytree(source, target)

    def sanitize_file(self, file_path):
        """Normalize file imports and remove unnecessary strings."""
        with open(file_path, "r") as f:
            contents = f.read()

        contents = contents.replace("from httplib2.", "from .")
        contents = contents.replace("from httplib2", "from .")
        contents = contents.replace(
            "import pyparsing as pp", "from ... import pyparsing as pp"
        )

        with open(file_path, "w") as f:
            f.write(contents)


def main(temp_path, repo_root, version):
    # Paths and file names
    httplib2_dir = repo_root / "shotgun_api3" / "lib" / "httplib2"
    python2_dir = str(httplib2_dir / "python2")
    python3_dir = str(httplib2_dir / "python3")
    file_name = f"{version}.zip"
    file_path = temp_path / file_name

    utilities = Utilities()

    # Downloads the archive from github
    utilities.download_archive(file_path, file_name)

    # Unzip in a temp dir
    unzipped_folder = temp_path / "unzipped"
    unzipped_folder.mkdir()
    utilities.unzip_archive(file_path, file_name, unzipped_folder)

    # Remove current httplib2/python2 and httplib2/python3 folders
    utilities.remove_folder(python2_dir)
    utilities.remove_folder(python3_dir)

    # Removes the previous version of httplib2
    utilities.git_remove([str(python2_dir), str(python3_dir)])

    # Copies a new version into place.
    print("Copying new version of httplib2")
    root_folder = unzipped_folder / f"httplib2-{version[1:]}"
    utilities.copy_folder(str(root_folder / "python2" / "httplib2"), python2_dir)
    utilities.copy_folder(str(root_folder / "python3" / "httplib2"), python3_dir)
    utilities.remove_folder(f"{python2_dir}/test")
    utilities.remove_folder(f"{python3_dir}/test")

    # Patches the httplib2 imports so they are relative instead of absolute.
    print("Patching imports")
    for python_file in httplib2_dir.rglob("*.py"):
        utilities.sanitize_file(python_file)

    # Adding files to the git repo.
    print("Adding to git")
    subprocess.check_output(["git", "add", str(python2_dir), str(python3_dir)])


if __name__ == "__main__":
    try:
        temp_path = pathlib.Path(tempfile.mkdtemp())
        main(temp_path, pathlib.Path(__file__).parent, sys.argv[1])
    finally:
        shutil.rmtree(temp_path)
