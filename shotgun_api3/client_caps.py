"""
 -----------------------------------------------------------------------------
 Copyright (c) 2009-2019, Shotgun Software Inc.

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

  - Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

  - Neither the name of the Shotgun Software Inc nor the names of its
    contributors may be used to endorse or promote products derived from this
    software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys


class ClientCapabilities(object):
    """
    Container for the client capabilities.

    .. warning::

        This class is part of the internal API and its interfaces may change at any time in
        the future. Therefore, usage of this class is discouraged.

    :ivar str platform: The current client platform. Valid values are ``mac``, ``linux``,
        ``windows``, or ``None`` (if the current platform couldn't be determined).
    :ivar str local_path_field: The SG field used for local file paths. This is calculated using
        the value of ``platform``. Ex. ``local_path_mac``.
    :ivar str py_version: Simple version of Python executable as a string. Eg. ``2.7``.
    :ivar str ssl_version: Version of OpenSSL installed. Eg. ``OpenSSL 1.0.2g  1 Mar 2016``. This
        info is only available in Python 2.7+ if the ssl module was imported successfully.
        Defaults to ``unknown``
    """

    def __init__(self):
        system = sys.platform.lower()

        if system == 'darwin':
            self.platform = "mac"
        elif system.startswith('linux'):
            self.platform = 'linux'
        elif system == 'win32':
            self.platform = 'windows'
        else:
            self.platform = None

        if self.platform:
            self.local_path_field = "local_path_%s" % self.platform
        else:
            self.local_path_field = None

        self.py_version = ".".join(str(x) for x in sys.version_info[:2])

        # extract the OpenSSL version if we can. The version is only available in Python 2.7 and
        # only if we successfully imported ssl
        self.ssl_version = "unknown"
        try:
            import ssl
            self.ssl_version = ssl.OPENSSL_VERSION
        except (ImportError, AttributeError, NameError):
            pass

    def __str__(self):
        return (
            "ClientCapabilities: platform %s, local_path_field %s, "
            "py_version %s, ssl version %s" % (
                self.platform,
                self.local_path_field,
                self.py_version,
                self.ssl_version
            )
        )
