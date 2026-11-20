"""Reference consumption-only service. TLS ingress/deployment are operator tasks.

No model key, provider request, candidate execution, grant creation or ref updates.
The service is disabled by the checked-in live config. Never start it on a broker.
"""
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .common import GateError, encoded, json_load, require
from .consumption import ConsumptionAuthority
from .github import APIError, GitHub
from .trial import Ledger, preflight


def handler(authority,token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass  # Never log headers, bodies or credentials.

        def do_POST(self):
            self.connection.settimeout(10)
            status,body=403,{'error':'consumption denied'}
            try:
                require(self.path=='/v1/consume','unsupported service operation')
                require(hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token),'unauthorized')
                length=int(self.headers.get('Content-Length','0'))
                require(0<length<=100_000,'invalid request size')
                body=authority.consume(json.loads(self.rfile.read(length)));status=200
            except APIError as error:
                status=409 if error.status in (409,422) else 503
                body={'error':'consumption unavailable or already used; stop'}
            except (GateError,ValueError,KeyError,TypeError,TimeoutError):pass
            raw=encoded(body).encode()
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    return Handler


def main():
    require(not os.environ.get('AUTOSE_MODEL_API_KEY'),'provider credentials forbidden in consumption authority')
    config=json_load('workflow/config/live.json');preflight(config)
    token=os.environ.get('AUTOSE_CONSUMER_TOKEN')
    require(token and os.environ.get('GITHUB_TOKEN'),'consumption service credentials missing')
    authority=ConsumptionAuthority(Ledger(GitHub()),config)
    # Bind loopback only; a separately reviewed HTTPS ingress authenticates clients.
    ThreadingHTTPServer(('127.0.0.1',8080),handler(authority,token)).serve_forever()


if __name__=='__main__':main()
