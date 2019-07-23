from .. import six

# import the proper implementation into the module namespace depending on the
# current python version.  httplib2 supports python 2/3 by forking the code rather
# than with a single cross-compatible module. Rather than modify third party code,
# we'll just import the appropriate branch here.
if six.PY3:
    from .python3 import *
    from .python3 import socks  # ensure include in namespace
    import ssl
    ssl_error_classes = (ssl.SSLError, ssl.CertificateError)
else:
    from .python2 import *
    from .python2 import socks  # ensure include in namespace
    from .python2 import SSLHandshakeError  # TODO: shouldn't rely on this. not public
    ssl_error_classes = (SSLHandshakeError,)
