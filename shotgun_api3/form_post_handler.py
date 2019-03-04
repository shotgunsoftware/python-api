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

import codecs
import io
import os
import stat

# proper import handled by __init__.py
from .lib import mimetypes
from .lib import six

# py2 & py3 compatibility issues
cStringIO = six.moves.cStringIO
url_request = six.moves.urllib.request
urlencode = six.moves.urllib.parse.urlencode

# allows file type checking in py2 & py3
if six.PY3:
    file_type = io.IOBase
else:
    file_type = file

# the `mimetools` module no longer exists in python 3. We can work around this
# by simply generating a random string to use as a separator between form data
# in a request. See here for more info: https://stackoverflow.com/a/27174474
if six.PY3:
    def choose_boundary():
        import uuid
        return uuid.uuid4()
else:
    import mimetools    # used for attachment upload
    choose_boundary = mimetools.choose_boundary


# Helpers from the previous API, left as is.
# Based on http://code.activestate.com/recipes/146306/
class FormPostHandler(url_request.BaseHandler):
    """
    Handler for multipart form data
    """
    handler_order = url_request.HTTPHandler.handler_order - 10  # needs to run first

    def http_request(self, request):
        # get_data was removed in 3.4. since we're testing against 3.6 and
        # 3.7, this should be sufficient.
        if six.PY3:
            data = request.data
        else:
            data = request.get_data()
        if data is not None and not isinstance(data, six.string_types):
            files = []
            params = []
            for key, value in data.items():
                if isinstance(value, file_type):
                    files.append((key, value))
                else:
                    params.append((key, value))
            if not files:
                if six.PY3:
                    data = urlencode(params, True).encode()
                else:
                    data = urlencode(params, True)  # sequencing on
            else:
                if six.PY3:
                    boundary, data = self.encode(params, files)
                else:
                    boundary, data = self.encode_py2(params, files)
                content_type = 'multipart/form-data; boundary=%s' % boundary
                request.add_unredirected_header('Content-Type', content_type)
            # add_data was removed in 3.4. since we're testing against 3.6 and
            # 3.7, this should be sufficient.
            if six.PY3:
                request.data = data
            else:
                request.add_data(data)
        return request

    def encode_py2(self, params, files, boundary=None, buffer=None):
        if boundary is None:
            boundary = choose_boundary()
        if buffer is None:
            buffer = cStringIO()
        for (key, value) in params:
            buffer.write('--%s\r\n' % boundary)
            buffer.write('Content-Disposition: form-data; name="%s"' % key)
            buffer.write('\r\n\r\n%s\r\n' % value)
        for (key, fd) in files:
            # On Windows, it's possible that we were forced to open a file
            # with non-ascii characters as unicode. In that case, we need to
            # encode it as a utf-8 string to remove unicode from the equation.
            # If we don't, the mix of unicode and strings going into the
            # buffer can cause UnicodeEncodeErrors to be raised.
            filename = fd.name
            if six.PY2 and isinstance(filename, six.text_type):
                filename = filename.encode("utf-8")
            filename = filename.split('/')[-1]
            content_type = mimetypes.guess_type(filename)[0]
            content_type = content_type or 'application/octet-stream'
            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
            buffer.write('--%s\r\n' % boundary)
            c_dis = 'Content-Disposition: form-data; name="%s"; filename="%s"%s'
            content_disposition = c_dis % (key, filename, '\r\n')
            buffer.write(content_disposition)
            buffer.write('Content-Type: %s\r\n' % content_type)
            buffer.write('Content-Length: %s\r\n' % file_size)
            fd.seek(0)
            buffer.write('\r\n%s\r\n' % fd.read())
        buffer.write('--%s--\r\n\r\n' % boundary)
        buffer = buffer.getvalue()
        return boundary, buffer

    def encode(self, params, files, boundary=None, buffer=None):

        if boundary is None:
            boundary = choose_boundary()

        boundary_str = "--%s\r\n" % boundary
        closing_boundary_str = "--%s--\r\n\r\n" % boundary

        if buffer is None:
            buffer = io.BytesIO()

        # here we ensure all key/values are strings. then we format them for the
        # post data. finally, write them to the buffer as bytes
        for (key, value) in params:

            # ---- ensure strings

            # key
            key = self._ensure_str(key)
            content_disposition = 'Content-Disposition: form-data; name="%s"\r\n' % key
            content_disposition = self._ensure_str(content_disposition)

            # value
            if isinstance(value, int) or isinstance(value, float):
                value = str(value)
            value = self._ensure_str(value)

            # encode the strings as utf-8 bytes and write to the buffer
            buffer.write(self._encode_utf8(boundary_str))
            buffer.write(self._encode_utf8(content_disposition))
            buffer.write(self._encode_utf8("\r\n"))
            buffer.write(self._encode_utf8(value))
            buffer.write(self._encode_utf8("\r\n"))

        for (key, fd) in files:

            # key
            key = self._ensure_str(key)

            file_path = self._ensure_str(fd.name)
            file_name = file_path.split('/')[-1]
            file_name = file_name

            file_size = os.fstat(fd.fileno())[stat.ST_SIZE]

            content_disposition = 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, file_name)
            content_disposition = self._ensure_str(content_disposition)

            content_type = mimetypes.guess_type(file_name)[0]
            content_type = content_type or 'application/octet-stream'

            content_type = "Content-Type: %s\r\n" % content_type
            content_length = "Content-Length: %s\r\n" % file_size

            fd.seek(0)
            file_buff = fd.read()

            # encode the strings as utf-8 bytes and write to the buffer
            buffer.write(self._encode_utf8(boundary_str))
            buffer.write(self._encode_utf8(content_disposition))
            buffer.write(self._encode_utf8(content_type))
            buffer.write(self._encode_utf8(content_length))
            buffer.write(self._encode_utf8("\r\n"))
            buffer.write(file_buff)
            buffer.write(self._encode_utf8("\r\n"))

        buffer.write(self._encode_utf8(closing_boundary_str))
        buffer = buffer.getvalue()
        return boundary, buffer

    def https_request(self, request):
        return self.http_request(request)

    def _ensure_str(self, source):
        # python 3 only
        if isinstance(source, six.binary_type):
            return source.decode("utf-8")
        else:
            return source

    def _encode_utf8(self, input):
        encoder = codecs.getencoder("utf-8")
        return encoder(input)[0]
