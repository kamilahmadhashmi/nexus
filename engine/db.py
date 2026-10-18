import logging
import os
import time
from falkordb import FalkorDB

logger = logging.getLogger("nexus.db")

HOST = os.getenv("FALKOR_HOST", "localhost")
PORT = int(os.getenv("FALKOR_PORT", "6379"))
PASSWORD = os.getenv("FALKOR_PASSWORD", None)
USERNAME = os.getenv("FALKOR_USERNAME", None)
SSL = os.getenv("FALKOR_SSL", "0").lower() in ("1", "true", "yes")
URL = os.getenv("FALKOR_URL", None)
MAIN = "nexus"
_client = None


def client():
    global _client
    if _client is not None:
        return _client

    # In serverless environments (e.g. Vercel) or when external DB is down, fail fast to simulator
    is_serverless = bool(os.getenv("VERCEL") or os.getenv("SERVERLESS") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    max_retries = 1 if is_serverless else 2
    retry_delay = 0.2
    last_error = None

    for _ in range(max_retries):
        try:
            if URL:
                connection = FalkorDB.from_url(URL)
            else:
                connection = FalkorDB(
                    host=HOST,
                    port=PORT,
                    password=PASSWORD,
                    username=USERNAME,
                    ssl=SSL,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.5,
                )
            connection.list_graphs()
            _client = connection
            return _client
        except Exception as exc:
            last_error = exc
            time.sleep(retry_delay)

    # Resilient fallback for serverless deployments (Vercel) when an external FalkorDB cluster is not reachable
    logger.warning("FalkorDB unreachable at %s:%s (%s); activating in-memory graph simulator.", HOST, PORT, last_error)
    from engine.in_memory import get_in_memory_client
    _client = get_in_memory_client()
    return _client


def graph(name=MAIN):
    return client().select_graph(name)
