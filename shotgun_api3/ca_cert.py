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

# this file shouldn't be imported until ssl is verified to be available
import ssl

from six.moves import http_client
from six.moves.urllib import request as url_request


class CACertsHTTPSConnection(http_client.HTTPConnection):
    """"
    This class allows to create an HTTPS connection that uses the custom certificates
    passed in.
    """

    default_port = http_client.HTTPS_PORT

    def __init__(self, *args, **kwargs):
        """
        :param args: Positional arguments passed down to the base class.
        :param ca_certs: Path to the custom CA certs file.
        :param kwargs: Keyword arguments passed down to the bas class
        """
        # Pop that argument,
        self.__ca_certs = kwargs.pop("ca_certs")
        http_client.HTTPConnection.__init__(self, *args, **kwargs)

    def connect(self):
        """Connect to a host on a given (SSL) port."""
        http_client.HTTPConnection.connect(self)
        # Now that the regular HTTP socket has been created, wrap it with our SSL certs.
        self.sock = ssl.wrap_socket(
            self.sock,
            ca_certs=self.__ca_certs,
            cert_reqs=ssl.CERT_REQUIRED
        )


class CACertsHTTPSHandler(url_request.HTTPSHandler):
    """
    Handler that ensures https connections are created with the custom CA certs.
    """
    def __init__(self, cacerts):
        url_request.HTTPSHandler.__init__(self)
        self.__ca_certs = cacerts

    def https_open(self, req):
        return self.do_open(self.create_https_connection, req)

    def create_https_connection(self, *args, **kwargs):
        return CACertsHTTPSConnection(*args, ca_certs=self.__ca_certs, **kwargs)
