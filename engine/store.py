import json
import os
import uuid

PATH = os.getenv("NEXUS_STORE", "data/investigations.json")


def _load():
    if not os.path.exists(PATH):
        return {}
    with open(PATH, encoding="utf-8") as handle:
        return json.load(handle)


def save(investigation_id, record):
    data = _load()
    data[investigation_id] = record
    directory = os.path.dirname(PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary_path = PATH + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(temporary_path, PATH)


def get(investigation_id):
    return _load().get(investigation_id)


def clear():
    data = {}
    directory = os.path.dirname(PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary_path = PATH + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    os.replace(temporary_path, PATH)


def new_id():
    return "INV-" + uuid.uuid4().hex[:6].upper()
