"""An OCI registry's read side, enough for the checks and the publisher: does a tag exist, what
labels does its image carry, which tags does a repository hold, and can a site pull it without a
token. The Docker registry API v2, with the bearer-token challenge every registry speaks
(`WWW-Authenticate: Bearer realm=…,service=…,scope=…`)."""
import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request

INDEX_TYPES = ("application/vnd.oci.image.index.v1+json",
               "application/vnd.docker.distribution.manifest.list.v2+json")
MANIFEST_TYPES = ("application/vnd.oci.image.manifest.v1+json",
                  "application/vnd.docker.distribution.manifest.v2+json")
ACCEPT = ", ".join(INDEX_TYPES + MANIFEST_TYPES)


class RegistryError(Exception):
    pass


class Unknown(RegistryError):
    """The registry would not say: an anonymous token refused, which ghcr.io answers alike for a
    repository never published and for a private one."""


class Registry:

    def __init__(self, host, user=None, password=None, insecure=False):
        self.host = host
        self.user, self.password = user, password
        self.scheme = "http" if insecure else "https"
        self._tokens = {}

    def anonymous(self):
        return Registry(self.host, insecure=self.scheme == "http")

    # -- the bearer challenge ------------------------------------------------------------------
    def _token(self, challenge, repository):
        params = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
        realm = params.pop("realm", None)
        if realm is None:
            raise RegistryError(f"{self.host}: a challenge without realm: {challenge}")
        params.setdefault("scope", f"repository:{repository}:pull")
        url = realm + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url)
        if self.user and self.password:
            cred = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            req.add_header("Authorization", "Basic " + cred)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                if self.password:
                    # a credential refused says nothing about the tag: never read it as "not published"
                    raise RegistryError(f"{self.host}/{repository}: the registry refuses the credential given ({e.code})") from None
                raise Unknown(f"{self.host}/{repository}: the registry refuses a token to an anonymous caller") from None
            raise RegistryError(f"{self.host}: the token endpoint answers {e.code}") from None
        return body.get("token") or body.get("access_token")

    def _request(self, method, repository, path, accept=None):
        url = f"{self.scheme}://{self.host}/v2/{repository}/{path}"
        for attempt in (0, 1):
            req = urllib.request.Request(url, method=method)
            if accept:
                req.add_header("Accept", accept)
            token = self._tokens.get(repository)
            if token:
                req.add_header("Authorization", "Bearer " + token)
            try:
                r = urllib.request.urlopen(req, timeout=60)
                return r.status, r.headers, (r.read() if method != "HEAD" else b"")
            except urllib.error.HTTPError as e:
                challenge = e.headers.get("WWW-Authenticate", "")
                if e.code == 401 and attempt == 0 and challenge.lower().startswith("bearer"):
                    self._tokens[repository] = self._token(challenge, repository)
                    continue
                return e.code, e.headers, b""
        return 401, {}, b""

    # -- what the tooling asks -----------------------------------------------------------------
    def exists(self, repository, tag):
        """True or False; raises Unknown when an anonymous caller cannot tell (the spec, §5.2)."""
        status, _, _ = self._request("HEAD", repository, f"manifests/{tag}", ACCEPT)
        if status == 200:
            return True
        if status == 404:
            return False
        if status in (401, 403):
            if self.password:
                raise RegistryError(f"{self.host}/{repository}:{tag}: the registry answers {status} to the credential given")
            raise Unknown(f"{self.host}/{repository}:{tag}: the registry answers {status}")
        raise RegistryError(f"{self.host}/{repository}:{tag}: the registry answers {status}")

    def _get_json(self, repository, path, accept):
        status, headers, body = self._request("GET", repository, path, accept)
        if status != 200:
            raise RegistryError(f"{self.host}/{repository}/{path}: {status}")
        return json.loads(body), headers

    def manifest(self, repository, tag):
        return self._get_json(repository, f"manifests/{tag}", ACCEPT)[0]

    def platforms(self, repository, tag):
        doc = self.manifest(repository, tag)
        if doc.get("mediaType") in INDEX_TYPES or "manifests" in doc:
            return sorted(f"{m['platform']['os']}/{m['platform']['architecture']}"
                          for m in doc["manifests"]
                          if m.get("platform", {}).get("os") not in (None, "unknown"))   # attestations
        return []

    def image(self, repository, tag, platform="linux/amd64"):
        """The image manifest of one platform, and its config."""
        doc = self.manifest(repository, tag)
        if "manifests" in doc:
            chosen = None
            for m in doc["manifests"]:
                p = m.get("platform", {})
                if f"{p.get('os')}/{p.get('architecture')}" == platform:
                    chosen = m
                    break
            if chosen is None:
                raise RegistryError(f"{repository}:{tag} has no {platform} image")
            doc = self._get_json(repository, f"manifests/{chosen['digest']}", ACCEPT)[0]
        config = self._get_json(repository, f"blobs/{doc['config']['digest']}", "*/*")[0]
        return doc, config

    def labels(self, repository, tag):
        return (self.image(repository, tag)[1].get("config") or {}).get("Labels") or {}

    def tags(self, repository):
        out, path = [], "tags/list?n=1000"
        while path:
            doc, headers = self._get_json(repository, path, "application/json")
            out += doc.get("tags") or []
            link = headers.get("Link", "") if headers else ""
            m = re.search(r"<([^>]+)>", link)
            path = m.group(1).split(f"/v2/{repository}/", 1)[-1] if m else None
        return out

    def forget(self, repository):
        """Drops the token cached for a repository: one taken before a push may not read what it pushed."""
        self._tokens.pop(repository, None)

    def anonymous_pull(self, repository, tag):
        try:
            return self.anonymous().exists(repository, tag)
        except Unknown:
            return False


def split_image(ref):
    """`ghcr.io/blsq/openclinic:0.2.0-rc.1` -> ('ghcr.io', 'blsq/openclinic', '0.2.0-rc.1')."""
    host, _, rest = ref.partition("/")
    name, _, tag = rest.rpartition(":")
    if not name or "/" in tag:
        raise ValueError(f"'{ref}' is not an image reference with a tag")
    return host, name, tag
