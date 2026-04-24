import json
import os

STATE_FILE = "pending_remediations.json"

def _load():
    """Charge depuis fichier JSON"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def _save(data):
    """Sauvegarde dans fichier JSON"""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[STATE] ❌ Erreur sauvegarde : {e}")

class PersistentDict:
    """Dictionnaire persistant dans un fichier JSON"""

    def __init__(self):
        self._data = _load()

    def __setitem__(self, key, value):
        self._data[key] = value
        _save(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]
        _save(self._data)

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def pop(self, key, default=None):
        val = self._data.pop(key, default)
        _save(self._data)
        return val

    def __len__(self):
        return len(self._data)

    def items(self):
        return self._data.items()

# Instance partagée persistante
pending_remediations = PersistentDict()