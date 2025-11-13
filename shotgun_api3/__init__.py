# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sys
import warnings

if sys.version_info < (3, 7):
    if os.environ.get("SHOTGUN_API_ALLOW_OLD_PYTHON", "0") != "1":
        raise Exception("This module requires Python version 3.7 or higher.")

    warnings.warn(
        "Python versions older than 3.7 are no longer supported as of January "
        "2023. Since the SHOTGUN_API_ALLOW_OLD_PYTHON variable is enabled, this "
        "module is raising a warning instead of an exception. "
        "However, it is very likely that this module will not be able to work "
        "on this Python version.",
        UserWarning,
        stacklevel=2,
    )
elif sys.version_info < (3, 9):
    warnings.warn(
        "Python versions older than 3.9 are no longer supported as of March "
        "2025 and compatibility will be discontinued after March 2026. "
        "Please update to Python 3.11 or any other supported version.",
        DeprecationWarning,
        stacklevel=2,
    )


from .shotgun import (
    Shotgun,
    ShotgunError,
    ShotgunFileDownloadError,  # noqa unused imports
    ShotgunThumbnailNotReady,
    Fault,
    AuthenticationFault,
    MissingTwoFactorAuthenticationFault,
    UserCredentialsNotAllowedForSSOAuthenticationFault,
    ProtocolError,
    ResponseError,
    Error,
    __version__,
)
from .shotgun import SG_TIMEZONE as sg_timezone  # noqa unused imports
