import json
import urllib.error
import urllib.parse
import urllib.request

from google.auth.transport.requests import Request
from google.oauth2 import service_account

from .config import (
    GOOGLE_PLAY_PACKAGE_NAME,
    GOOGLE_PLAY_SERVICE_ACCOUNT_FILE,
)

ANDROID_PUBLISHER_SCOPE = "https://www.googleapis.com/auth/androidpublisher"


class GooglePlayConfigError(RuntimeError):
    pass


class GooglePlayVerificationError(RuntimeError):
    pass


def _build_credentials():
    if not GOOGLE_PLAY_SERVICE_ACCOUNT_FILE:
        raise GooglePlayConfigError("GOOGLE_PLAY_SERVICE_ACCOUNT_FILE təyin edilməyib.")

    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_PLAY_SERVICE_ACCOUNT_FILE,
        scopes=[ANDROID_PUBLISHER_SCOPE],
    )
    credentials.refresh(Request())
    return credentials


def _authorized_headers():
    credentials = _build_credentials()
    return {
        "Authorization": f"Bearer {credentials.token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def verify_one_time_purchase(product_id: str, purchase_token: str) -> dict:
    url = (
        "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
        f"{urllib.parse.quote(GOOGLE_PLAY_PACKAGE_NAME, safe='')}/purchases/products/"
        f"{urllib.parse.quote(product_id, safe='')}/tokens/"
        f"{urllib.parse.quote(purchase_token, safe='')}"
    )
    request = urllib.request.Request(url, headers=_authorized_headers(), method="GET")

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise GooglePlayVerificationError(
            f"Google Play verify xətası: HTTP {exc.code} {error_body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise GooglePlayVerificationError(f"Google Play bağlantı xətası: {exc}") from exc


def acknowledge_one_time_purchase(product_id: str, purchase_token: str):
    url = (
        "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
        f"{urllib.parse.quote(GOOGLE_PLAY_PACKAGE_NAME, safe='')}/purchases/products/"
        f"{urllib.parse.quote(product_id, safe='')}/tokens/"
        f"{urllib.parse.quote(purchase_token, safe='')}:acknowledge"
    )
    payload = json.dumps({"developerPayload": "premium_lifetime"}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers=_authorized_headers(),
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20):
            return
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise GooglePlayVerificationError(
            f"Google Play acknowledge xətası: HTTP {exc.code} {error_body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise GooglePlayVerificationError(f"Google Play bağlantı xətası: {exc}") from exc
