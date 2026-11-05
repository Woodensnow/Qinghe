"""JSON persistence; callers hold LOCK across each complete API transaction."""
import json
import os
import threading
from pathlib import Path
from datetime import datetime, timedelta, timezone
from auth_utils import hash_password

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / 'data.json'
LOCK = threading.RLock()
_db = None


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def build_seed():
    db = json.loads((ROOT / 'seed-data.json').read_text(encoding='utf-8'))
    salt, digest = hash_password('qinghe123')
    db['users'][0].update(salt=salt, passwordHash=digest)
    db['sessions'] = []
    today = datetime.now().date()
    now = datetime.now(timezone.utc)
    for booking, days, age in zip(db['bookings'], (7, -18), (2, 26)):
        booking['date'] = (today + timedelta(days=days)).isoformat()
        booking['createdAt'] = (now - timedelta(days=age)).isoformat().replace('+00:00', 'Z')
    # Keep the demo chat's relative chronology on every reset.
    anchor = datetime.fromisoformat(db['conversations'][0]['updatedAt'].replace('Z', '+00:00'))
    delta = now - timedelta(minutes=45) - anchor
    for item in db['conversations'] + db['messages']:
        for key in ('createdAt', 'updatedAt'):
            if key in item:
                item[key] = (datetime.fromisoformat(item[key].replace('Z', '+00:00')) + delta).isoformat().replace('+00:00', 'Z')
    return db


def data():
    global _db
    if _db is None:
        if DATA_FILE.exists():
            # Never overwrite existing accounts if their data cannot be read.
            _db = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        else:
            _db = build_seed()
            save()
        _db.setdefault('conversations', [])
        _db.setdefault('messages', [])
    return _db


def save():
    if _db is not None:
        tmp = DATA_FILE.with_suffix('.json.tmp')
        with tmp.open('w', encoding='utf-8') as stream:
            json.dump(_db, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, DATA_FILE)


def reset():
    global _db
    with LOCK:
        _db = build_seed()
        save()
