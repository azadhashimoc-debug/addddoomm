import argparse
import threading
from typing import Optional

from demucs.pretrained import get_model

_status_lock = threading.Lock()
_status = {
    "state": "idle",
    "message": "Model hələ hazırlanmayıb."
}


def _set_status(state: str, message: str) -> None:
    with _status_lock:
        _status["state"] = state
        _status["message"] = message


def get_model_status() -> dict:
    with _status_lock:
        return dict(_status)


def is_model_ready() -> bool:
    return get_model_status()["state"] == "ready"


def warmup_model(model_name: str = "htdemucs") -> bool:
    current = get_model_status()["state"]
    if current == "ready":
        return True
    if current == "warming":
        return False

    _set_status("warming", f"{model_name} modeli əvvəlcədən yüklənir...")
    try:
        get_model(model_name)
        _set_status("ready", f"{model_name} modeli hazırdır.")
        return True
    except Exception as exc:
        _set_status("error", f"Model warmup xətası: {exc}")
        return False


def warmup_in_background(model_name: str = "htdemucs") -> None:
    thread = threading.Thread(target=warmup_model, args=(model_name,), daemon=True)
    thread.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="htdemucs")
    args = parser.parse_args()
    ok = warmup_model(args.name)
    raise SystemExit(0 if ok else 1)
