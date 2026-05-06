import os
import threading
from typing import Callable
import zmq

ZMQ_URL = os.getenv("ZMQ_URL", "tcp://127.0.0.1:28332")

_on_tx: Callable | None = None
_on_block: Callable | None = None


def on_tx(cb: Callable) -> None:
    global _on_tx
    _on_tx = cb


def on_block(cb: Callable) -> None:
    global _on_block
    _on_block = cb


def _listen() -> None:
    ctx = zmq.Context()
    sock = ctx.socket(zmq.SUB)
    sock.connect(ZMQ_URL)
    sock.setsockopt(zmq.SUBSCRIBE, b"hashtx")
    sock.setsockopt(zmq.SUBSCRIBE, b"hashblock")

    while True:
        parts = sock.recv_multipart()
        topic = parts[0]
        body  = parts[1]
        hex_data = body.hex()

        if topic == b"hashtx" and _on_tx:
            _on_tx(hex_data)
        elif topic == b"hashblock" and _on_block:
            _on_block(hex_data)


def start() -> None:
    threading.Thread(target=_listen, daemon=True, name="zmq-listener").start()
