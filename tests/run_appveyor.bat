:: Copyright (c) 2018 Shotgun Software Inc.
::
:: CONFIDENTIAL AND PROPRIETARY
::
:: This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
:: Source Code License included in this distribution package. See LICENSE.
:: By accessing, using, copying or modifying this work you indicate your
:: agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
:: not expressly granted therein are reserved by Shotgun Software Inc.

::
:: This file is run by the appveyor builds.
::

copy tests\example_config tests\config
%PYTHON%\Scripts\pip install -r tests/ci_requirements.txt
:: Set the SHOTGUN_API_CACERTS env var to point at the distributed cacerts.
set SHOTGUN_API_CACERTS=shotgun_api3\lib\httplib2\python2\cacerts.txt
%PYTHON%\Scripts\nosetests.exe -v --config="nose.cfg"
