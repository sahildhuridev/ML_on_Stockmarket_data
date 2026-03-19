from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd
from django.conf import settings

from sentiment_analysis.models import SentimentArtifact


def get_data_root() -> Path:
    return Path(getattr(settings, "SENTIMENT_DATA_ROOT", settings.BASE_DIR / "data"))


def get_job_root(job) -> Path:
    return get_data_root() / "sentiment_analysis" / f"job_{job.pk}_{job.ticker.upper()}"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def stable_hash(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def write_json(job, layer: str, artifact_type: str, payload) -> str:
    file_path = get_job_root(job) / layer / f"{artifact_type}.json"
    ensure_parent(file_path)
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
    return str(file_path)


def write_csv(job, layer: str, artifact_type: str, rows: list[dict]) -> str:
    file_path = get_job_root(job) / layer / f"{artifact_type}.csv"
    ensure_parent(file_path)
    fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else ["empty"]
    with file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return str(file_path)


def write_parquet(job, layer: str, artifact_type: str, rows: list[dict]) -> tuple[str, str]:
    parquet_path = get_job_root(job) / layer / f"{artifact_type}.parquet"
    ensure_parent(parquet_path)
    frame = pd.DataFrame(rows)
    try:
        frame.to_parquet(parquet_path, index=False)
        return str(parquet_path), "parquet"
    except Exception:
        fallback_path = get_job_root(job) / layer / f"{artifact_type}.json"
        with fallback_path.open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2, default=str)
        return str(fallback_path), "json"


def register_artifact(job, layer: str, artifact_type: str, file_path: str, file_format: str, row_count: int = 0, metadata_json: dict | None = None) -> SentimentArtifact:
    return SentimentArtifact.objects.create(
        job=job,
        layer=layer,
        artifact_type=artifact_type,
        file_path=file_path,
        file_format=file_format,
        row_count=row_count,
        metadata_json=metadata_json or {},
    )


def dedupe_records(records: list[dict]) -> list[dict]:
    seen = set()
    unique_records = []
    for record in records:
        record_hash = stable_hash(record)
        if record_hash in seen:
            continue
        seen.add(record_hash)
        unique_records.append(record)
    return unique_records
