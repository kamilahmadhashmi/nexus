import json
import os
import uuid

# In serverless environments (e.g. AWS Lambda / Vercel), current working directory is read-only.
# Only /tmp is writable.
if os.getenv("VERCEL") or os.getenv("SERVERLESS") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    PATH = os.getenv("NEXUS_STORE", "/tmp/investigations.json")
else:
    PATH = os.getenv("NEXUS_STORE", "data/investigations.json")

_MEM_STORE = {}


def _load():
    global _MEM_STORE
    if not os.path.exists(PATH):
        return dict(_MEM_STORE)
    try:
        with open(PATH, encoding="utf-8") as handle:
            loaded = json.load(handle)
            _MEM_STORE.update(loaded)
            return dict(_MEM_STORE)
    except Exception:
        return dict(_MEM_STORE)


def save(investigation_id, record):
    global _MEM_STORE
    _MEM_STORE[investigation_id] = record
    try:
        data = _load()
        data[investigation_id] = record
        directory = os.path.dirname(PATH)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temporary_path = PATH + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(temporary_path, PATH)
    except Exception:
        pass


def get(investigation_id):
    loaded = _load()
    if investigation_id in loaded:
        return loaded[investigation_id]
    return _MEM_STORE.get(investigation_id)


def clear():
    global _MEM_STORE
    _MEM_STORE.clear()
    try:
        data = {}
        directory = os.path.dirname(PATH)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temporary_path = PATH + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        os.replace(temporary_path, PATH)
    except Exception:
        pass


def new_id():
    return "INV-" + uuid.uuid4().hex[:6].upper()

