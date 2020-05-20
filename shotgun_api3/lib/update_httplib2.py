#!/usr/bin/env python3

import pathlib
import tempfile
import shutil
import subprocess
import sys

def main(temp_path, version):
    file_name = f"{version}.zip"

    print(f"Downloading {file_name}")
    file_path = temp_path / file_name
    subprocess.check_output(["curl", "-L", f"https://github.com/httplib2/httplib2/archive/{file_name}", "-o", file_path])

    print(f"Unzipping {file_name}")
    unzipped_folder = temp_path / "unzipped"
    unzipped_folder.mkdir()
    subprocess.check_output(["unzip", str(file_path), "-d", str(unzipped_folder)])
    shutil.rmtree("httplib2/python2")
    shutil.rmtree("httplib2/python3")

    print("Removing previous version of httplib2")
    subprocess.check_output(["git", "rm", "-rf", "httplib2/python2", "httplib2/python3"])

    print("Copying new version of httplib2")
    root_folder = unzipped_folder / f"httplib2-{version[1:]}"
    shutil.copytree(str(root_folder / "python2/httplib2"), "httplib2/python2")
    shutil.copytree(str(root_folder / "python3/httplib2"), "httplib2/python3")
    shutil.rmtree("httplib2/python2/test")
    shutil.rmtree("httplib2/python3/test")

    print("Patching imports")
    for python_file in pathlib.Path("httplib2").rglob("*.py"):
        subprocess.check_output(
            ["sed",  "-i", "", "-e" "s/from httplib2/from ./g", python_file]
        )

    print("Adding to git")
    subprocess.check_output(["git", "add", "httplib2/python2", "httplib2/python3"])


try:
    temp_path = pathlib.Path(tempfile.mkdtemp())
    main(temp_path, sys.argv[1])
finally:
    pass # shutil.rmtree(temp_path)