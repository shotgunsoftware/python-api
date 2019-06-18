from .. import six

# import the proper implementation into the module namespace depending on the
# current python version
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
