# -*- coding: utf-8 -*-
"""The module containing HTTPProxyDigestAuth."""
import re

from requests import auth
from requests import cookies


class HTTPProxyDigestAuth(auth.HTTPDigestAuth):
    """HTTP digest authentication between proxy

    :param stale_rejects: The number of rejects indicate that:
        the client may wish to simply retry the request
        with a new encrypted response, without reprompting the user for a
        new username and password. i.e., retry build_digest_header
    :type stale_rejects: int
    """
    _pat = re.compile(r'digest ', flags=re.IGNORECASE)

    def __init__(self, *args, **kwargs):
        super(HTTPProxyDigestAuth, self).__init__(*args, **kwargs)
        self.stale_rejects = 0

    def handle_407(self, r, **kwargs):
        """Handle HTTP 407 only once, otherwise give up

        :param r: current response
        :returns: responses, along with the new response
        """
        if r.status_code == 407 and self.stale_rejects < 2:
            if "proxy-authenticate" not in r.headers:
                raise IOError(
                    "proxy server violated RFC 7235:"
                    "407 response MUST contain header proxy-authenticate")
            self.chal = cookies.parse_dict_header(
                self._pat.sub('', r.headers['proxy-authenticate'], count=1))

            # if we present the user/passwd and still get rejected
            # http://tools.ietf.org/html/rfc2617#section-3.2.1
            if ('Proxy-Authorization' in r.request.headers and
                    'stale' in self.chal):
                if self.chal['stale'].lower() == 'true':  # try again
                    self.stale_rejects += 1
                # wrong user/passwd
                elif self.chal['stale'].lower() == 'false':
                    raise IOError("User or password is invalid")

            # Consume content and release the original connection
            # to allow our new request to reuse the same one.
            r.content
            r.close()
            prep = r.request.copy()
            cookies.extract_cookies_to_jar(prep._cookies, r.request, r.raw)
            prep.prepare_cookies(prep._cookies)

            prep.headers['Proxy-Authorization'] = self.build_digest_header(
                prep.method, prep.url)
            _r = r.connection.send(prep, **kwargs)
            _r.history.append(r)
            _r.request = prep

            return _r
        else:  # give up authenticate
            return r

    def __call__(self, r):
        # if we have nonce, then just use it, otherwise server will tell us
        if self.last_nonce:
            r.headers['Proxy-Authorization'] = self.build_digest_header(
                r.method, r.url
            )
        r.register_hook('response', self.handle_407)
        return r
