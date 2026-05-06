import time
from rpc import node_rpc

# Buckets em sat/vB  [lower_bound, upper_bound)
BUCKETS = [1, 2, 3, 5, 10, 20, 50, 100, float("inf")]
LABELS  = ["1-2", "2-3", "3-5", "5-10", "10-20", "20-50", "50-100", "100+"]

# Cores associadas a cada bucket (exportadas para o frontend)
COLORS = ["#3fb950", "#5cb85c", "#8bc34a", "#cddc39",
          "#d29922", "#f0883e", "#f85149", "#b00020"]

# Estado interno
_state: dict[str, dict] = {}   # txid -> {fee_rate, vsize, time}
_last_rebuild = 0.0
MIN_REBUILD_INTERVAL = 2.0     # segundos


def _bucket(rate: float) -> int:
    for i in range(len(BUCKETS) - 1):
        if BUCKETS[i] <= rate < BUCKETS[i + 1]:
            return i
    return len(LABELS) - 1


def rebuild(force: bool = False) -> bool:
    """Reconstrói o estado a partir de getrawmempool.
    Retorna True se o rebuild foi executado, False se foi ignorado (throttle)."""
    global _state, _last_rebuild
    now = time.time()
    if not force and (now - _last_rebuild) < MIN_REBUILD_INTERVAL:
        return False
    _last_rebuild = now
    try:
        raw = node_rpc("getrawmempool", [True])
    except Exception:
        return False

    new_state = {}
    for txid, info in raw.items():
        vsize = info.get("vsize") or 1
        fee_btc = info.get("fees", {}).get("base", 0)
        rate = (fee_btc * 1e8) / vsize
        new_state[txid] = {
            "fee_rate": round(rate, 2),
            "vsize": vsize,
            "time": info.get("time", 0),
        }
    _state = new_state
    return True


def get_histogram() -> dict:
    counts = [0] * len(LABELS)
    vsizes = [0] * len(LABELS)
    for data in _state.values():
        i = _bucket(data["fee_rate"])
        counts[i] += 1
        vsizes[i] += data["vsize"]
    return {"labels": LABELS, "counts": counts, "vsizes": vsizes, "colors": COLORS}


def get_stats() -> dict:
    if not _state:
        return {"tx_count": 0, "min_rate": 0, "max_rate": 0, "avg_rate": 0, "total_vsize": 0}
    rates = [d["fee_rate"] for d in _state.values()]
    vsizes = [d["vsize"] for d in _state.values()]
    return {
        "tx_count": len(rates),
        "min_rate": round(min(rates), 2),
        "max_rate": round(max(rates), 2),
        "avg_rate": round(sum(rates) / len(rates), 2),
        "total_vsize": sum(vsizes),
    }


def get_current_txids() -> set:
    return set(_state.keys())


def get_fee_rate(txid: str) -> float | None:
    entry = _state.get(txid)
    return entry["fee_rate"] if entry else None


def detect_purged(pre_txids: set, confirmed_txids: set) -> list[dict]:
    """Retorna txids que saíram da mempool sem ser confirmadas (evicted/purging)."""
    post_txids = get_current_txids()
    purged_ids = pre_txids - post_txids - confirmed_txids
    result = []
    for txid in purged_ids:
        result.append({"txid": txid, "fee_rate": None})
    return result
