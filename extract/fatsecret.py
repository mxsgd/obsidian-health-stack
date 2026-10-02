"""FatSecret food diary -> raw_fatsecret.daily (kcal, protein, carbs, fat per logged day).

Diary data belongs to a user, so it needs OAuth 1.0 3-legged auth (OAuth 2.0 only reaches the public food database).
One-time setup: approve the app in the browser, token + secret are appended to .env:
    uv run python -m extract.fatsecret
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import date, timedelta
from pathlib import Path

from extract.load import replace

API = "https://platform.fatsecret.com/rest/server.api"
AUTH = "https://authentication.fatsecret.com/oauth/"
EPOCH = date(1970, 1, 1)  # FatSecret dates are "date_int": days since epoch
NUTRIENTS = ["calories", "protein", "carbohydrate", "fat"]


def q(s) -> str:
    return urllib.parse.quote(str(s), safe="")  # RFC 3986, as the OAuth 1.0 signature requires


def call(method: str, url: str, params: dict, token: str = "", token_secret: str = "") -> bytes:
    """Signed (and, with a token, delegated) OAuth 1.0 HMAC-SHA1 request."""
    params = {**params, "oauth_consumer_key": os.environ["FATSECRET_CONSUMER_KEY"], "oauth_signature_method": "HMAC-SHA1",
              "oauth_timestamp": str(int(time.time())), "oauth_nonce": secrets.token_hex(8), "oauth_version": "1.0"}
    if token:
        params["oauth_token"] = token
    normalized = "&".join(f"{q(k)}={q(v)}" for k, v in sorted(params.items()))
    base = "&".join(q(p) for p in (method, url, normalized))
    key = f"{q(os.environ['FATSECRET_CONSUMER_SECRET'])}&{q(token_secret)}"
    params["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()

    body = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    req = (urllib.request.Request(url, data=body.encode(), method="POST") if method == "POST"
           else urllib.request.Request(f"{url}?{body}"))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"FatSecret {e.code}: {e.read().decode(errors='replace')}") from None


def api(method: str, **params) -> dict:
    res = json.loads(call("GET", API, {"method": method, "format": "json", **params},
                          os.environ["FATSECRET_TOKEN"], os.environ["FATSECRET_TOKEN_SECRET"]))
    if "error" in res:
        raise RuntimeError(f"FatSecret {method}: {res['error']}")
    return res


def authorize(env_file: Path):
    """3-legged OAuth with oob callback: the browser shows a code, you paste it here."""
    req = dict(urllib.parse.parse_qsl(call("POST", AUTH + "request_token", {"oauth_callback": "oob"}).decode()))
    url = f"{AUTH}authorize?oauth_token={q(req['oauth_token'])}"
    print(f"Approve access in the browser (opening {url}), then paste the code it shows.")
    webbrowser.open(url)
    verifier = input("code: ").strip()
    acc = dict(urllib.parse.parse_qsl(call("GET", AUTH + "access_token", {"oauth_verifier": verifier},
                                           req["oauth_token"], req["oauth_token_secret"]).decode()))
    with env_file.open("a", encoding="utf-8") as f:
        f.write(f"\nFATSECRET_TOKEN={acc['oauth_token']}\nFATSECRET_TOKEN_SECRET={acc['oauth_token_secret']}\n")
    print(f"Saved FATSECRET_TOKEN and FATSECRET_TOKEN_SECRET to {env_file}")


def run(con, since: date):
    days, month = [], since.replace(day=1)
    while month <= date.today():
        days += api("food_entries.get_month.v2", date=(month - EPOCH).days)["month"].get("day", [])
        month = (month + timedelta(days=32)).replace(day=1)
    rows = [{"date": EPOCH + timedelta(days=int(d["date_int"])), **{k: d.get(k) for k in NUTRIENTS}} for d in days]
    replace(con, "raw_fatsecret", "daily", {"date": "date", **{k: "varchar" for k in NUTRIENTS}}, rows)


if __name__ == "__main__":
    from run import ROOT, load_env

    load_env()
    authorize(ROOT / ".env")
