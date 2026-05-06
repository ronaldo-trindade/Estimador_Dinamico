import os
import requests

RPC_USER = os.getenv("RPC_USER", "bitcoin")
RPC_PASSWORD = os.getenv("RPC_PASSWORD", "password")
RPC_HOST = os.getenv("RPC_HOST", "127.0.0.1")
RPC_PORT = os.getenv("RPC_PORT", "8332")

_url = f"http://{RPC_HOST}:{RPC_PORT}"


def node_rpc(method: str, params: list | None = None):
    payload = {
        "jsonrpc": "1.0",
        "id": "estimador",
        "method": method,
        "params": params or [],
    }
    r = requests.post(_url, json=payload, auth=(RPC_USER, RPC_PASSWORD), timeout=60)
    r.raise_for_status()
    body = r.json()
    if body.get("error"):
        raise RuntimeError(body["error"])
    return body["result"]
