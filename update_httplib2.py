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

def main(temp_path, repo_root, version):
    # Output folders for the python2 and python3 copies of httplib2
    httplib2_dir = repo_root / "shotgun_api3" / "lib" / "httplib2"
    python2_dir = str(httplib2_dir / "python2")
    python3_dir = str(httplib2_dir / "python3")

    file_name = f"{version}.zip"
    # Downloads the archive from github.
    print(f"Downloading {file_name}")
    file_path = temp_path / file_name
    subprocess.check_output(["curl", "-L", f"https://github.com/httplib2/httplib2/archive/{file_name}", "-o", file_path])

    # Unzips in a temp dir.
    print(f"Unzipping {file_name}")
    unzipped_folder = temp_path / "unzipped"
    unzipped_folder.mkdir()
    subprocess.check_output(["unzip", str(file_path), "-d", str(unzipped_folder)])
    shutil.rmtree(python2_dir)
    shutil.rmtree(python3_dir)

    # Removes the previous version of httplib2
    print("Removing previous version of httplib2")
    subprocess.check_output(["git", "rm", "-rf", str(python2_dir), str(python3_dir)])

    # Copies a new version into place.
    print("Copying new version of httplib2")
    root_folder = unzipped_folder / f"httplib2-{version[1:]}"
    shutil.copytree(str(root_folder / "python2" / "httplib2"), python2_dir)
    shutil.copytree(str(root_folder / "python3" / "httplib2"), python3_dir)
    shutil.rmtree(f"{python2_dir}/test")
    shutil.rmtree(f"{python3_dir}/test")

    # Patches the httplib2 imports so they are relative instead of absolute.
    print("Patching imports")
    for python_file in httplib2_dir.rglob("*.py"):
        subprocess.check_output(
            ["sed", "-i", "", "-e" "s/from httplib2/from ./g", python_file]
        )

    # Adding files to the git repo.
    print("Adding to git")
    subprocess.check_output(["git", "add", str(python2_dir), str(python3_dir)])


try:
    temp_path = pathlib.Path(tempfile.mkdtemp())
    main(temp_path, pathlib.Path(__file__).parent, sys.argv[1])
finally:
    shutil.rmtree(temp_path)
