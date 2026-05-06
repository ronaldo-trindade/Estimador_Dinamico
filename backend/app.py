import os
import pathlib
import threading
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
import mempool
import zmq_listener
from rpc import node_rpc

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

FRONTEND_DIR  = pathlib.Path(__file__).parent.parent / "frontend"
STATIC_DIR    = FRONTEND_DIR / "static"

# txid -> socket session id
_watched: dict[str, str] = {}
_watched_lock = threading.Lock()

# ── Helpers ──────────────────────────────────────────────────────────────────

def _fee_estimates() -> dict:
    targets = {"next_block": 1, "three_blocks": 3, "six_blocks": 6, "one_day": 144}
    result = {}
    for key, blocks in targets.items():
        try:
            r = node_rpc("estimatesmartfee", [blocks, "ECONOMICAL"])
            feerate_btc_kb = r.get("feerate")
            if feerate_btc_kb is not None:
                sat_vb = round(feerate_btc_kb * 1e8 / 1000, 2)
                result[key] = {"sat_vb": sat_vb, "blocks": r.get("blocks", blocks)}
            else:
                result[key] = {"sat_vb": None, "blocks": blocks, "error": r.get("errors", ["?"])[0]}
        except Exception as e:
            result[key] = {"sat_vb": None, "blocks": blocks, "error": str(e)}
    return result


def _block_txids(block_hash: str) -> set:
    try:
        block = node_rpc("getblock", [block_hash, 1])
        return set(block.get("tx", []))
    except Exception:
        return set()


def _block_info(block_hash: str) -> dict:
    try:
        block = node_rpc("getblock", [block_hash, 1])
        return {
            "hash": block_hash,
            "height": block.get("height"),
            "tx_count": len(block.get("tx", [])),
            "time": block.get("time"),
            "size": block.get("size"),
            "weight": block.get("weight"),
        }
    except Exception:
        return {"hash": block_hash}


def _broadcast_mempool():
    socketio.emit("mempool_update", {
        "histogram": mempool.get_histogram(),
        "stats": mempool.get_stats(),
    })


# ── ZMQ callbacks ─────────────────────────────────────────────────────────────

def _on_new_tx(txid: str) -> None:
    if mempool.rebuild():
        _broadcast_mempool()


def _on_new_block(block_hash: str) -> None:
    pre_txids = mempool.get_current_txids()

    confirmed_txids = _block_txids(block_hash)
    info = _block_info(block_hash)

    mempool.rebuild(force=True)
    _broadcast_mempool()

    purged = mempool.detect_purged(pre_txids, confirmed_txids)
    estimates = _fee_estimates()

    socketio.emit("fee_estimate", estimates)
    socketio.emit("block_found", {**info, "purged_count": len(purged)})

    if purged:
        socketio.emit("tx_purged", {"txids": purged})

    # Verificar txids monitoradas
    with _watched_lock:
        to_notify = {txid: sid for txid, sid in _watched.items() if txid in confirmed_txids}
        for txid in to_notify:
            del _watched[txid]

    for txid, sid in to_notify.items():
        socketio.emit("tx_confirmed", {"txid": txid, "block_hash": block_hash}, to=sid)


# ── Socket.IO events ──────────────────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    # Envia estado atual ao cliente que acabou de conectar
    emit("mempool_update", {
        "histogram": mempool.get_histogram(),
        "stats": mempool.get_stats(),
    })
    emit("fee_estimate", _fee_estimates())


@socketio.on("watch_tx")
def on_watch_tx(data):
    from flask import request
    txid = (data.get("txid") or "").strip()
    if len(txid) == 64:
        with _watched_lock:
            _watched[txid] = request.sid
        emit("watch_ack", {"txid": txid, "status": "watching"})
    else:
        emit("watch_ack", {"txid": txid, "status": "invalid"})


@socketio.on("unwatch_tx")
def on_unwatch_tx(data):
    txid = (data.get("txid") or "").strip()
    with _watched_lock:
        _watched.pop(txid, None)


# ── HTTP routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    resp = send_from_directory(FRONTEND_DIR, "index.html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/assets/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


@app.route("/api/mempool")
def api_mempool():
    from flask import jsonify
    return jsonify({"histogram": mempool.get_histogram(), "stats": mempool.get_stats()})


@app.route("/api/fees")
def api_fees():
    from flask import jsonify
    return jsonify(_fee_estimates())


# ── Startup ───────────────────────────────────────────────────────────────────
# Roda tanto com `python3 app.py` quanto com gunicorn (que não executa __main__)

def _startup():
    mempool.rebuild(force=True)
    zmq_listener.on_tx(_on_new_tx)
    zmq_listener.on_block(_on_new_block)
    zmq_listener.start()

_startup()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
