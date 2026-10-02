"""OAuth 1.0 signature check against the published Twitter/RFC 5849 example. Run: uv run python -m extract.test_fatsecret"""
import os
import urllib.parse
from unittest import mock

from extract import fatsecret

os.environ |= {"FATSECRET_CONSUMER_KEY": "xvz1evFS4wEEPTGEFPHBog",
               "FATSECRET_CONSUMER_SECRET": "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw"}
sent = {}


def fake_urlopen(req, timeout):
    sent.update(urllib.parse.parse_qsl(req.data.decode()))
    return mock.MagicMock(**{"__enter__.return_value.read.return_value": b""})


with (mock.patch("time.time", return_value=1318622958),
      mock.patch("secrets.token_hex", return_value="kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg"),
      mock.patch("urllib.request.urlopen", fake_urlopen)):
    fatsecret.call("POST", "https://api.twitter.com/1/statuses/update.json",
                   {"include_entities": "true", "status": "Hello Ladies + Gentlemen, a signed OAuth request!"},
                   "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb", "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE")

assert sent["oauth_signature"] == "tnnArxj06cWHq44gCs1OSKk/jLY=", sent["oauth_signature"]
print("fatsecret checks pass")
