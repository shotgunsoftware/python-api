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

from .errors import ShotgunError


class ServerCapabilities(object):
    """
    Container for the servers capabilities, such as version enabled features.

    .. warning::

        This class is part of the internal API and its interfaces may change at any time in
        the future. Therefore, usage of this class is discouraged.
    """

    def __init__(self, host, meta):
        """
        ServerCapabilities.__init__

        :param str host: Host name for the server excluding protocol.
        :param dict meta: dict of meta data for the server returned from the info() api method.

        :ivar str host:
        :ivar dict server_info:
        :ivar tuple version: Simple version of the Shotgun server. ``(major, minor, rev)``
        :ivar bool is_dev: ``True`` if server is running a development version of the Shotgun
            codebase.
        """
        # Server host name
        self.host = host
        self.server_info = meta

        # Version from server is major.minor.rev or major.minor.rev."Dev"
        # Store version as tuple and check dev flag
        try:
            self.version = meta.get("version", None)
        except AttributeError:
            self.version = None
        if not self.version:
            raise ShotgunError("The Shotgun Server didn't respond with a version number. "
                               "This may be because you are running an older version of "
                               "Shotgun against a more recent version of the Shotgun API. "
                               "For more information, please contact Shotgun Support.")

        if len(self.version) > 3 and self.version[3] == "Dev":
            self.is_dev = True
        else:
            self.is_dev = False

        self.version = tuple(self.version[:3])
        self._ensure_json_supported()

    def _ensure_support(self, feature, raise_hell=True):
        """
        Checks the server version supports a given feature, raises an exception if it does not.

        :param dict feature: dict where **version** key contains a 3 integer tuple indicating the
            supported server version and **label** key contains a human-readable label str::

                { 'version': (5, 4, 4), 'label': 'project parameter }
        :param bool raise_hell: Whether to raise an exception if the feature is not supported.
            Defaults to ``True``
        :raises: :class:`ShotgunError` if the current server version does not support ``feature``
        """

        if not self.version or self.version < feature['version']:
            if raise_hell:
                raise ShotgunError(
                    "%s requires server version %s or higher, "
                    "server is %s" % (feature['label'], _version_str(feature['version']), _version_str(self.version))
                )
            return False
        else:
            return True

    def _ensure_json_supported(self):
        """
        Ensures server has support for JSON API endpoint added in v2.4.0.
        """
        self._ensure_support({
            'version': (2, 4, 0),
            'label': 'JSON API'
        })

    def ensure_include_archived_projects(self):
        """
        Ensures server has support for archived Projects feature added in v5.3.14.
        """
        self._ensure_support({
            'version': (5, 3, 14),
            'label': 'include_archived_projects parameter'
        })

    def ensure_per_project_customization(self):
        """
        Ensures server has support for per-project customization feature added in v5.4.4.
        """
        return self._ensure_support({
            'version': (5, 4, 4),
            'label': 'project parameter'
        }, True)

    def ensure_support_for_additional_filter_presets(self):
        """
        Ensures server has support for additional filter presets feature added in v7.0.0.
        """
        return self._ensure_support({
            'version': (7, 0, 0),
            'label': 'additional_filter_presets parameter'
        }, True)

    def ensure_user_following_support(self):
        """
        Ensures server has support for listing items a user is following, added in v7.0.12.
        """
        return self._ensure_support({
            'version': (7, 0, 12),
            'label': 'user_following parameter'
        }, True)

    def ensure_paging_info_without_counts_support(self):
        """
        Ensures server has support for optimized pagination, added in v7.4.0.
        """
        return self._ensure_support({
            'version': (7, 4, 0),
            'label': 'optimized pagination'
        }, False)

    def ensure_return_image_urls_support(self):
        """
        Ensures server has support for returning thumbnail URLs without additional round-trips, added in v3.3.0.
        """
        return self._ensure_support({
            'version': (3, 3, 0),
            'label': 'return thumbnail URLs'
        }, False)

    def __str__(self):
        return "ServerCapabilities: host %s, version %s, is_dev %s"\
                 % (self.host, self.version, self.is_dev)


def _version_str(version):
    """
    Convert a tuple of int's to a '.' separated str.
    """
    return '.'.join(map(str, version))
