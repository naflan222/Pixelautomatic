from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


class AutomationError(Exception):
    """A safe, operator-readable error without credentials or request bodies."""


class ApiError(AutomationError):
    def __init__(self, service, status, code=None):
        self.status = status
        self.code = code
        super().__init__(f"{service} request failed (HTTP {status}, code {code or 'unavailable'}).")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def local_day():
    return datetime.now(ZoneInfo("Asia/Colombo")).date()


def due(kind, day, start):
    elapsed = (day - date.fromisoformat(start)).days
    return elapsed >= 0 and (kind == "image" or elapsed % 3 == 0)


def load_config(path="config.json"):
    c = json.loads(Path(path).read_text())
    date.fromisoformat(c["start_date"])
    if c.get("timezone") != "Asia/Colombo":
        raise AutomationError("This workflow uses the Asia/Colombo timezone.")
    if c.get("website") != "https://pixelhouse.lk":
        raise AutomationError("Review the importer before changing the store origin.")
    if c.get("language") not in ("en", "si", "mixed"):
        raise AutomationError("Language must be en, si, or mixed.")
    if not c.get("platforms") or any(p not in ("facebook", "instagram") for p in c["platforms"]):
        raise AutomationError("Select facebook and/or instagram only.")
    if not re.fullmatch(r"v\d+\.\d+", c["graph_version"]):
        raise AutomationError("Invalid Meta Graph version.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", c["state_branch"]):
        raise AutomationError("State branch name must contain letters, numbers, _ or -.")
    if c.get("video_seconds") != 20:
        raise AutomationError("The validated fallback exports 20-second videos.")
    return c


def request(url, *, method="GET", headers=None, body=None, service="Remote", limit=20_000_000):
    headers = {"User-Agent": "Pixelhouse-Automation/1.0", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    # Only GET requests are retried. POST/PUT ambiguity is handled by durable checkpoints.
    for attempt in range(3 if method == "GET" else 1):
        try:
            opener = urllib.request.build_opener()
            if "Authorization" in headers:
                class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self, *args, **kwargs):
                        return None
                opener = urllib.request.build_opener(NoAuthRedirect)
            with opener.open(req, timeout=60) as response:
                raw = response.read(limit + 1)
                if len(raw) > limit:
                    raise AutomationError(f"{service} response exceeded the size limit.")
                return raw
        except urllib.error.HTTPError as exc:
            status = exc.code
            if method == "GET" and status in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            code = None
            try:
                payload = json.loads(exc.read(8192))
                code = payload.get("error", {}).get("code")
            except (ValueError, AttributeError):
                pass
            raise ApiError(service, status, code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            if method == "GET" and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise AutomationError(f"{service} network request failed. Inspect saved publication state before retrying.") from None


def json_request(url, **kwargs):
    try:
        return json.loads(request(url, **kwargs))
    except (ValueError, UnicodeError):
        raise AutomationError("Provider returned an invalid JSON response.") from None


def store_image(url):
    u = urllib.parse.urlparse(url)
    if u.scheme != "https" or u.netloc != "pixelhouse.lk":
        raise AutomationError("Product image is not on the approved Pixelhouse origin.")
    # A redirect may legitimately serve a CDN; this store is reviewed for its own origin only.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    try:
        opener = urllib.request.build_opener(NoRedirect)
        with opener.open(urllib.request.Request(url, headers={"User-Agent": "Pixelhouse-Automation/1.0"}), timeout=30) as r:
            raw = r.read(15_000_001)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise AutomationError("Could not download the original product photograph.") from None
    if len(raw) > 15_000_000:
        raise AutomationError("Product photograph is too large.")
    return raw


def products():
    payload = json_request("https://pixelhouse.lk/api/products", service="Pixelhouse catalog")
    if not isinstance(payload, dict) or not isinstance(payload.get("products"), list):
        raise AutomationError("Product feed changed. No content will be published.")
    result = []
    for p in payload["products"]:
        if not isinstance(p, dict) or not p.get("id") or not p.get("name") or not p.get("slug") or not p.get("image"):
            continue
        image = urllib.parse.urljoin("https://pixelhouse.lk/", p["image"])
        if urllib.parse.urlparse(image).netloc != "pixelhouse.lk" or not image.startswith("https://"):
            continue
        raw_price = p.get("price")
        price = None
        if isinstance(raw_price, (int, float)) and not isinstance(raw_price, bool) and 0 < raw_price < 1_000_000_000:
            price = raw_price
        stock = p.get("stock")
        result.append({"id": str(p["id"]), "name": str(p["name"])[:250], "price": price,
                       "stock": stock if type(stock) is int else None, "image": image,
                       "url": "https://pixelhouse.lk/single-product.html?slug=" + urllib.parse.quote(str(p["slug"]), safe=""),
                       "category": str(p.get("category", "")), "verified_at": utc_now()})
    if not result:
        raise AutomationError("The live catalog is empty. Holding publication.")
    return result


def select_product(catalog, state, day, kind, excluded=()):
    excluded = {str(x) for x in excluded}
    eligible = [p for p in catalog if type(p["stock"]) is int and p["stock"] > 0 and p["id"] not in excluded]
    if not eligible:
        raise AutomationError("No verified in-stock products available.")
    history = [post for post in state["posts"].values() if post.get("product")]
    recent = {p["product"]["id"] for p in sorted(history, key=lambda p: p["slot"], reverse=True)[:7]}
    def rank(p):
        uses = [post["slot"] for post in history if post["product"]["id"] == p["id"]]
        tie = hashlib.sha256(f"{day}:{kind}:{p['id']}".encode()).hexdigest()
        return p["id"] in recent, max(uses, default=""), tie
    return sorted(eligible, key=rank)[0]


def assert_current(product, catalog):
    current = next((p for p in catalog if p["id"] == product["id"]), None)
    if not current or type(current["stock"]) is not int or current["stock"] <= 0:
        raise AutomationError("Product is no longer verified in stock; holding publication.")
    for field in ("price", "name", "image", "url"):
        if current[field] != product[field]:
            raise AutomationError(f"Product {field} changed after generation; create a fresh draft after review.")
    return current


HOOKS = ["Make every adventure count.", "Your next story starts here.", "Capture a fresh perspective.",
         "Find your next creative angle.", "Bring your next story into focus.", "Ready for your next adventure?"]


def plan(product, day, kind, language):
    index = int(hashlib.sha256(f"{day}:{kind}:{product['id']}".encode()).hexdigest()[:8], 16)
    hook = HOOKS[index % len(HOOKS)]
    price = "" if product["price"] is None else f" · LKR {product['price']:,.0f}"
    if language == "si":
        hook = "ඔබේ ඊළඟ නිර්මාණයට නව දැක්මක්."
    elif language == "mixed":
        hook = "ඔබේ next adventure එකට ready ද?"
    category = product["category"].lower()
    tags = ["#Pixelhouse", "#PhotographySriLanka", "#CameraAccessories"]
    if "gopro" in category or "gopro" in product["name"].lower():
        tags.append("#GoProSriLanka")
    elif "osmo" in category or "dji" in product["name"].lower():
        tags.append("#DJISriLanka")
    else:
        tags.append("#ContentCreator")
    # Exact verified price is rendered without rounding away fractional values.
    if product["price"] is not None and product["price"] % 1:
        price = f" · LKR {product['price']:,.2f}"
    caption = f"{hook}\n{product['name']}{price}\nExplore at Pixelhouse: {product['url']}\n{' '.join(tags)}"
    if len(caption) > 2200:
        raise AutomationError("Caption exceeds platform limit.")
    return {"headline": HOOKS[index % len(HOOKS)], "hook": "Your next adventure starts here.",
            "caption": caption, "design_seed": index, "product": product,
            "slot": f"{day}-{kind}", "date": str(day), "kind": kind, "created_at": utc_now()}


class GitHubStore:
    """Optimistic JSON checkpoints and public media in a dedicated repository branch."""
    path = "automation/state.json"

    def __init__(self, repo, token, branch):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise AutomationError("Set GITHUB_REPOSITORY to owner/repository.")
        if not token:
            raise AutomationError("GitHub Actions supplies GITHUB_TOKEN automatically; local publishing needs a scoped token.")
        self.repo, self.branch = repo, branch
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        self.sha = None
        self.state = {"version": 1, "posts": {}}

    def api(self, path, *, method="GET", body=None):
        return json_request(f"https://api.github.com/repos/{self.repo}/{path}", method=method, headers=self.headers, body=body, service="GitHub", limit=50_000_000)

    def load(self):
        info = self.api("")
        if info.get("private"):
            raise AutomationError("This free media transport requires a public repository. Private raw assets cannot be fetched by Meta.")
        self.default_branch = info["default_branch"]
        self.branch_exists = True
        try:
            self.api("git/ref/heads/" + self.branch)
        except ApiError as exc:
            if exc.status != 404:
                raise
            self.branch_exists = False
            return self.state
        try:
            record = self.api("contents/" + self.path + "?ref=" + self.branch)
        except ApiError as exc:
            if exc.status == 404:
                # Never silently erase a missing ledger on an existing state branch.
                raise AutomationError("State branch exists but its ledger is missing. Restore it before publishing.") from None
            raise
        self.sha = record["sha"]
        if record.get("encoding") == "base64":
            raw = base64.b64decode(record["content"])
        else:
            raw = request(f"https://raw.githubusercontent.com/{self.repo}/{self.branch}/{self.path}", service="State ledger", limit=20_000_000)
        self.state = json.loads(raw)
        if self.state.get("version") != 1 or not isinstance(self.state.get("posts"), dict):
            raise AutomationError("Unrecognized state ledger. Do not reset posting history.")
        return self.state

    def save(self):
        if not self.branch_exists:
            base = self.api("git/ref/heads/" + urllib.parse.quote(self.default_branch, safe=""))
            self.api("git/refs", method="POST", body={"ref": "refs/heads/" + self.branch, "sha": base["object"]["sha"]})
            self.branch_exists = True
        body = {"message": "Record Pixelhouse automation checkpoint", "branch": self.branch,
                "content": base64.b64encode(json.dumps(self.state, ensure_ascii=False, indent=2).encode()).decode()}
        if self.sha:
            body["sha"] = self.sha
        result = self.api("contents/" + self.path, method="PUT", body=body)
        self.sha = result["content"]["sha"]

    def upload(self, file):
        # Every media name is content-addressed. A pinned commit URL is immutable.
        raw = Path(file).read_bytes()
        if len(raw) > 30_000_000:
            raise AutomationError("Media exceeds the reviewed GitHub transport limit.")
        digest = hashlib.sha256(raw).hexdigest()
        name = f"automation/media/{digest}{Path(file).suffix}"
        try:
            existing = self.api("contents/" + name + "?ref=" + self.branch)
            # Recover an upload whose response was lost: the unique path identifies exact bytes.
            if not existing.get("sha"):
                raise AutomationError("Unexpected existing media record.")
            commit = self.api("git/ref/heads/" + self.branch)["object"]["sha"]
        except ApiError as exc:
            if exc.status != 404:
                raise
            r = self.api("contents/" + name, method="PUT", body={"message": "Store Pixelhouse public marketing media", "branch": self.branch, "content": base64.b64encode(raw).decode()})
            commit = r["commit"]["sha"]
        url = f"https://raw.githubusercontent.com/{self.repo}/{commit}/{name}"
        # Verify public, cookie-free delivery before handing the URL to Meta.
        fetched = request(url, service="Public marketing media", limit=30_000_000)
        if hashlib.sha256(fetched).hexdigest() != digest:
            raise AutomationError("Public media checksum failed.")
        return url


class Meta:
    def __init__(self, version, token, page_id, instagram_id):
        if not token or not re.fullmatch(r"\d+", page_id or ""):
            raise AutomationError("Add META_PAGE_ACCESS_TOKEN and FACEBOOK_PAGE_ID in GitHub Secrets.")
        self.version, self.token, self.page_id, self.instagram_id = version, token, page_id, instagram_id

    def call(self, path, body=None):
        return json_request(f"https://graph.facebook.com/{self.version}/{path}", method="POST" if body is not None else "GET", headers={"Authorization": f"Bearer {self.token}"}, body=body, service="Meta")

    def check(self, platforms):
        me = self.call("me?fields=id,name")
        if str(me.get("id")) != self.page_id:
            raise AutomationError("The token is not a Page token for FACEBOOK_PAGE_ID. Do not use a user token.")
        if "instagram" in platforms:
            if not re.fullmatch(r"\d+", self.instagram_id or ""):
                raise AutomationError("Add INSTAGRAM_ACCOUNT_ID in GitHub Secrets.")
            page = self.call(f"{self.page_id}?fields=instagram_business_account")
            if str(page.get("instagram_business_account", {}).get("id")) != self.instagram_id:
                raise AutomationError("Instagram professional account is not linked to the configured Page.")
        return {"page": me.get("name", "Authorized Page"), "platforms": platforms}

    def upload_reel(self, url, media_url):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "rupload.facebook.com":
            raise AutomationError("Meta returned an unexpected video upload origin.")
        return json_request(url, method="POST", headers={"Authorization": f"OAuth {self.token}", "file_url": media_url}, service="Meta Reel upload")
