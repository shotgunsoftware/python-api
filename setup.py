from setuptools import setup, find_packages
from codecs import open
from os import path
import pypandoc

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file and convert it to rst
long_description = pypandoc.convert('README.md', 'rst')

# Get the license details from the LICENSE file
with open(path.join(here, 'LICENSE'), encoding='utf-8') as f:
    license = f.read()

packages = find_packages(exclude=['tests'])

setup(
    name='shotgun-api3',
    version='3.0.30',
    description='Shotgun Python API',
    long_description=long_description,
    url='https://github.com/shotgunsoftware/python-api',
    author='Shotgun Software',
    author_email='support@shotgunsoftware.com',
    license='BSD',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='shotgun api development vfx animation games',
    packages=packages,
    package_data={
        '': ['LICENSE', 'NOTICE'], 
        'lib/httplib2': ['cacerts.txt']
    },
    include_package_data=True,
    zip_safe=False,
)

