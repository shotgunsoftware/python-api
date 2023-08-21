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

f = open('README.md')
readme = f.read().strip()

f = open('LICENSE')
license = f.read().strip()

script_args = sys.argv[1:]

setup(
    name='shotgun_api3',
    version='3.3.5',
    description='Shotgun Python API ',
    long_description=readme,
    author='Shotgun Software',
    author_email='https://developer.shotgridsoftware.com',
    url='https://github.com/shotgunsoftware/python-api',
    license=license,
    packages=find_packages(exclude=('tests',)),
    script_args=script_args,
    include_package_data=True,
    package_data={'': ['cacerts.txt', 'cacert.pem']},
    zip_safe=False,
    python_requires='>=3.7.0',
    install_requires=[
          'httplib2>=0.19.1',
          'certifi>=2022.12.7',
      ],
)
