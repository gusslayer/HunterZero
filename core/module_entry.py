import json
import os
import sys
import time
from pathlib import Path


def main(module_id: str) -> int:
    heartbeat_name = os.environ.get("HUNTERZERO_HEARTBEAT")
    if not heartbeat_name:
        print(json.dumps({"module": module_id, "status": "ready", "message": "Demo informativa"}))
        return 0
    heartbeat_path = Path(heartbeat_name)
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = heartbeat_path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps({
        "module": module_id,
        "status": "ready",
        "updated_at": time.time(),
    }), encoding="utf-8")
    temporary_path.replace(heartbeat_path)
    print(json.dumps({
        "module": module_id,
        "status": "informational_only",
        "message": "Plantilla segura; no ejecuta operaciones del sistema.",
    }))
    sys.stdout.flush()
    return 0
