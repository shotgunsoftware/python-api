"""A python wrapper for the accessing the Shotgun API
See:
http://shotgunsoftware.com
https://github.com/shotgunsoftware/python-api
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path
import pypandoc


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
# long_description = pypandoc.convert('README.md', 'rst')
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    license = f.read()

# Get the license details from the LICENSE file
with open(path.join(here, 'LICENSE'), encoding='utf-8') as f:
    license = f.read()

setup(
    name='shotgun-api3',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='3.0.26',

    description='Shotgun Python API',
    
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/shotgunsoftware/python-api',

    # Author details
    author='Shotgun Software',
    author_email='support@shotgunsoftware.com',

    # Choose your license
    license=license,

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 5 - Production/Stable',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Internet',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: BSD License',

        'Natural Language :: English',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],

    # What does your project relate to?
    keywords='shotgun api development vfx animation games',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['tests']),

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #   py_modules=["my_module"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    # TODO: look into simplejson requirements and per python version syntax
    install_requires=[],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    # extras_require={
    #     'test': ['nose', 'coverage'],
    # },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    # package_data={
    #     '': ['cacerts.txt'],
    # },
    package_data={'': ['LICENSE', 'NOTICE'], 'lib/httplib2': ['cacerts.txt']},
    data_files=[('', ['LICENSE', 'NOTICE'])],
    zip_safe=False,

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    # entry_points={
    #     'console_scripts': [
    #         'sample=sample:main',
    #     ],
    # },
)


# import sys
# from setuptools import setup, find_packages

# f = open('README.md')
# readme = f.read().strip()

# f = open('LICENSE')
# license = f.read().strip()

# # For python 2.4 support
# script_args = sys.argv[1:]
# if (sys.version_info[0] <= 2) or (sys.version_info[0] == 2 and sys.version_info[1] <= 5):
#     if 'install' in script_args and '--no-compile' not in script_args:
#         script_args.append('--no-compile')


# setup(
#     name='shotgun_api3',
#     version='3.0.25',
#     description='Shotgun Python API ',
#     long_description=readme,
#     author='Shotgun Software',
#     author_email='support@shotgunsoftware.com',
#     url='https://github.com/shotgunsoftware/python-api',
#     license=license,
#     packages=find_packages(exclude=('tests',)),
#     script_args=script_args,
#     include_package_data=True,
#     package_data={'': [ 'cacerts.txt']},
#     zip_safe=False,
# )
