# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='shotgun_api3',
    version='3.0.9.beta2',
    description='Shotgun Python API ',
    long_description=readme,
    author='Shotgun Software',
    author_email='',
    url='https://github.com/shotgunsoftware/python-api',
    license=license,
    packages=find_packages(exclude=('tests', ))
)
