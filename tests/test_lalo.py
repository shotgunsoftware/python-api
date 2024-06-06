def _get_path(url):
    """Returns path component of a url without the sheme, host, query, anchor, or any other
    additional elements.
    For example, the url "https://foo.shotgunstudio.com/page/2128#Shot_1190_sr10101_034"
    returns "/page/2128"
    """
    if isinstance(url, dict):
        return url.get('path')
    elif isinstance(url, tuple):
        # 3rd component is the path
        return url[2]
    else:
        return url.path

from urllib.parse import urlparse
url = "https://foo.shotgunstudio.com/page/2128#Shot_1190_sr10101_034"
print("url: ",url)
print("url: ", type(url))
result = urlparse(url)

print("_get_path: ", _get_path(result))