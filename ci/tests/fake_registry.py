"""A registry in a thread, for the tests: manifests and blobs from a dict, a bearer token that
anonymous callers may be refused, and the 401 challenge a real registry sends."""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeRegistry:

    def __init__(self, deny_anonymous_token=False, require_token=True, deny_every_token=False):
        self.repos = {}            # repository -> {"manifests": {ref: (mediatype, bytes)}, "blobs": {digest: bytes}}
        self.deny_anonymous_token = deny_anonymous_token
        self.require_token = require_token
        self.deny_every_token = deny_every_token
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.host = f"127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()

    def put_image(self, repository, tag, labels, platforms=("linux/amd64", "linux/arm64")):
        import hashlib
        r = self.repos.setdefault(repository, {"manifests": {}, "blobs": {}})

        def blob(data):
            d = "sha256:" + hashlib.sha256(data).hexdigest()
            r["blobs"][d] = data
            return d, len(data)
        entries = []
        for p in platforms:
            os_, arch = p.split("/")
            cfg = json.dumps({"architecture": arch, "os": os_, "config": {"Labels": labels}}).encode()
            cd, cs = blob(cfg)
            man = json.dumps({"schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
                              "config": {"mediaType": "application/vnd.oci.image.config.v1+json", "digest": cd, "size": cs},
                              "layers": []}).encode()
            md, ms = blob(man)
            r["manifests"][md] = ("application/vnd.oci.image.manifest.v1+json", man)
            entries.append({"mediaType": "application/vnd.oci.image.manifest.v1+json", "digest": md, "size": ms,
                            "platform": {"os": os_, "architecture": arch}})
        index = json.dumps({"schemaVersion": 2, "mediaType": "application/vnd.oci.image.index.v1+json",
                            "manifests": entries}).encode()
        r["manifests"][tag] = ("application/vnd.oci.image.index.v1+json", index)

    def _handler(reg):
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body=b"", ctype="application/json", headers=None):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

            def do_HEAD(self):
                self.do_GET()

            def do_GET(self):
                if self.path.startswith("/token"):
                    auth = self.headers.get("Authorization", "")
                    if reg.deny_every_token or (reg.deny_anonymous_token and not auth.startswith("Basic ")):
                        return self._send(403, b'{"errors":[{"code":"DENIED"}]}')
                    return self._send(200, b'{"token":"t0k3n"}')
                if reg.require_token and self.headers.get("Authorization") != "Bearer t0k3n":
                    return self._send(401, b"{}", headers={"WWW-Authenticate":
                        f'Bearer realm="http://{reg.host}/token",service="fake",scope="repository:x:pull"'})
                path = self.path.split("?")[0]
                if not path.startswith("/v2/"):
                    return self._send(404)
                rest = path[4:]
                for kind in ("manifests", "blobs", "tags"):
                    marker = f"/{kind}/"
                    if marker in rest:
                        repository, ref = rest.split(marker, 1)
                        break
                else:
                    return self._send(404)
                r = reg.repos.get(repository)
                if r is None:
                    return self._send(404, b'{"errors":[{"code":"NAME_UNKNOWN"}]}')
                if kind == "tags":
                    tags = [t for t in r["manifests"] if not t.startswith("sha256:")]
                    return self._send(200, json.dumps({"name": repository, "tags": tags}).encode())
                if kind == "manifests":
                    if ref not in r["manifests"]:
                        return self._send(404, b'{"errors":[{"code":"MANIFEST_UNKNOWN"}]}')
                    mt, body = r["manifests"][ref]
                    return self._send(200, body, mt)
                if ref not in r["blobs"]:
                    return self._send(404)
                return self._send(200, r["blobs"][ref], "application/octet-stream")
        return H
