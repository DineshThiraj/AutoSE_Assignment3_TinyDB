"""Bounded trusted-service transport. No retry, redirect or caller-selected URL."""
import json
import urllib.error
import urllib.parse
import urllib.request

from .common import GateError, encoded, require


def https_url(value):
    require(isinstance(value,str), 'trusted service URL missing')
    parsed=urllib.parse.urlsplit(value)
    require(parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password
            and not parsed.query and not parsed.fragment and parsed.port in (None,443), 'invalid trusted service URL')
    return value


def post_json(url, value, token, *, timeout=30, maximum=2_000_000):
    https_url(url)
    require(isinstance(token,str) and token, 'trusted service credential unavailable')
    request=urllib.request.Request(url,data=encoded(value).encode(),method='POST',
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    try:
        with urllib.request.build_opener(NoRedirect()).open(request,timeout=timeout) as response:
            raw=response.read(maximum+1)
        require(len(raw)<=maximum,'trusted service response too large')
        result=json.loads(raw)
    except (urllib.error.URLError,TimeoutError,json.JSONDecodeError):
        raise GateError('trusted service unavailable; no retry; any consumed authorization stays burned') from None
    require(isinstance(result,dict),'trusted service response malformed')
    return result
