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
import warnings

if sys.version_info < (3, 9):
    warnings.warn(
        "Python versions older than 3.9 are no longer supported since 2025-03 "
        "and compatibility will be removed at any time after end of March 2026. "
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
