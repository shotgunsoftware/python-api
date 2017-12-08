# -*- coding: utf-8 -*-
import sys
from setuptools import setup, find_packages

f = open('README.md')
readme = f.read().strip()

f = open('LICENSE')
license = f.read().strip()

# For python 2.4 support
script_args = sys.argv[1:]
if (sys.version_info[0] <= 2) or (sys.version_info[0] == 2 and sys.version_info[1] <= 5):
    if 'install' in script_args and '--no-compile' not in script_args:
        script_args.append('--no-compile')


setup(
    name='shotgun_api3',
    version='3.0.35',
    description='Shotgun Python API ',
    long_description=readme,
    author='Shotgun Software',
    author_email='support@shotgunsoftware.com',
    url='https://github.com/shotgunsoftware/python-api',
    license=license,
    packages=find_packages(exclude=('tests',)),
    script_args=script_args,
    include_package_data=True,
    package_data={'': ['cacerts.txt']},
    zip_safe=False,
)
