# -*- coding: utf-8 -*-
# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
from setuptools import setup, find_packages

f = open("README.md")
readme = f.read().strip()

f = open("LICENSE")
license = f.read().strip()

setup(
    name="shotgun_api3",
    version="3.8.4",
    description="Flow Production Tracking Python API",
    long_description=readme,
    author="Autodesk",
    author_email="https://www.autodesk.com/support/contact-support",
    url="https://github.com/shotgunsoftware/python-api",
    license=license,
    packages=find_packages(exclude=("tests",)),
    script_args=sys.argv[1:],
    include_package_data=True,
    package_data={"": ["cacerts.txt", "cacert.pem"]},
    zip_safe=False,
    python_requires=">=3.7.0",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
)
