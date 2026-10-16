import os
import time
from falkordb import FalkorDB

HOST = os.getenv("FALKOR_HOST", "localhost")
PORT = int(os.getenv("FALKOR_PORT", "6379"))
MAIN = "nexus"
_client = None


def client():
    global _client
    if _client is None:
        last_error = None
        for _ in range(30):
            try:
                connection = FalkorDB(host=HOST, port=PORT)
                connection.list_graphs()
                _client = connection
                break
            except Exception as exc:
                last_error = exc
                time.sleep(1)
        if _client is None:
            raise RuntimeError(f"Cannot reach FalkorDB at {HOST}:{PORT}: {last_error}")
    return _client


def graph(name=MAIN):
    return client().select_graph(name)
