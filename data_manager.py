"""Local persistence for clients and platform CSV reads."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent
CLIENTS_PATH = ROOT / "clients.json"
DATA_DIR = ROOT / "data"
LOGOS_DIR = DATA_DIR / "logos"
UPLOADS_DIR = DATA_DIR / "uploads"

SOURCE_FILES: dict[str, str] = {
    "cm360": "cm360.csv",
    "google_ads": "gads.csv",
    "meta": "meta.csv",
    "pacing": "pacing.csv",
}

DEFAULT_SOURCES: dict[str, bool] = {
    "cm360": False,
    "google_ads": False,
    "meta": False,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _empty_client(
    name: str,
    description: str = "",
    logo_path: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "description": description.strip(),
        "logo_path": logo_path,
        "created_at": _now_iso(),
        "sources": dict(DEFAULT_SOURCES),
        "media_plan": "",
        "ptc_export": None,
        "ptc_taxonomy": None,
        "ptc_narrative": None,
    }


def load_clients() -> list[dict[str, Any]]:
    _ensure_dirs()
    if not CLIENTS_PATH.exists():
        seed = [
            _empty_client(
                "Northstar Athletic",
                "Retail de calzado performance. Control de solapamiento entre Meta y Search.",
            ),
        ]
        save_clients(seed)
        return seed

    raw = json.loads(CLIENTS_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return raw


def save_clients(clients: list[dict[str, Any]]) -> None:
    _ensure_dirs()
    CLIENTS_PATH.write_text(
        json.dumps(clients, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def list_clients() -> list[dict[str, Any]]:
    return load_clients()


def get_client(client_id: str) -> dict[str, Any] | None:
    for client in load_clients():
        if client.get("id") == client_id:
            return client
    return None


def create_client(
    name: str,
    description: str = "",
    logo_path: str | None = None,
) -> dict[str, Any]:
    clients = load_clients()
    client = _empty_client(name, description, logo_path)
    clients.append(client)
    save_clients(clients)
    return client


def update_client(client_id: str, **fields: Any) -> dict[str, Any] | None:
    clients = load_clients()
    updated: dict[str, Any] | None = None
    allowed = {
        "name", "description", "logo_path", "sources", "media_plan",
        "ptc_export", "ptc_taxonomy", "ptc_narrative",
    }
    for index, client in enumerate(clients):
        if client.get("id") != client_id:
            continue
        for key, value in fields.items():
            if key in allowed:
                client[key] = value
        clients[index] = client
        updated = client
        break
    if updated is None:
        return None
    save_clients(clients)
    return updated


def delete_client(client_id: str) -> bool:
    clients = load_clients()
    remaining = [c for c in clients if c.get("id") != client_id]
    if len(remaining) == len(clients):
        return False
    clear_ptc_export(client_id)
    save_clients(remaining)
    return True


def set_source_connected(client_id: str, source: str, connected: bool = True) -> dict[str, Any] | None:
    if source not in DEFAULT_SOURCES:
        raise ValueError(f"Unknown source: {source}")
    client = get_client(client_id)
    if client is None:
        return None
    sources = dict(client.get("sources") or DEFAULT_SOURCES)
    sources[source] = connected
    return update_client(client_id, sources=sources)


def store_logo(client_id: str, filename: str, content: bytes) -> str:
    _ensure_dirs()
    suffix = Path(filename).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        suffix = ".png"
    dest = LOGOS_DIR / f"{client_id}{suffix}"
    dest.write_bytes(content)
    relative = str(dest.relative_to(ROOT))
    update_client(client_id, logo_path=relative)
    return relative


def store_ptc_export(client_id: str, filename: str, content: bytes) -> dict[str, Any]:
    """Persist a CM360 path-to-conversion export so the report survives a reload."""
    _ensure_dirs()
    destination = UPLOADS_DIR / client_id
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "cm360_path_to_conversion.csv"
    path.write_bytes(content)
    record = {
        "filename": filename,
        "path": str(path.relative_to(ROOT)),
        "size": len(content),
        "uploaded_at": _now_iso(),
    }
    update_client(client_id, ptc_export=record)
    return record


def read_ptc_export(client: dict[str, Any]) -> bytes | None:
    record = client.get("ptc_export")
    if not record or not record.get("path"):
        return None
    path = ROOT / record["path"]
    return path.read_bytes() if path.exists() else None


def clear_ptc_export(client_id: str) -> None:
    client = get_client(client_id)
    if client:
        record = client.get("ptc_export") or {}
        path = ROOT / record["path"] if record.get("path") else None
        if path and path.exists():
            path.unlink()
    folder = UPLOADS_DIR / client_id
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
    update_client(client_id, ptc_export=None, ptc_taxonomy=None, ptc_narrative=None)


def read_source(source: str) -> pd.DataFrame:
    if source not in SOURCE_FILES:
        raise ValueError(f"Unknown source: {source}")
    path = DATA_DIR / SOURCE_FILES[source]
    if not path.exists():
        raise FileNotFoundError(f"Missing export: {path.name}")
    return pd.read_csv(path)


def source_available(source: str) -> bool:
    filename = SOURCE_FILES.get(source)
    if not filename:
        return False
    return (DATA_DIR / filename).exists()
