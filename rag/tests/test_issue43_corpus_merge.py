"""Offline checks for corpus merging and version-bound label manifests."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from rag.scripts.merge_issue43_corpus import merge_records, prepare
from rag.src.ingestion.cleaner import content_hash


def record(
    url="https://www.incibe.es/ciudadania/avisos/test",
    text="Aviso de fraude de prueba.",
):
    scraped = datetime.now(UTC) - timedelta(days=1)
    return {
        "url": url,
        "source": "incibe",
        "title": "Aviso",
        "text": text,
        "content_hash": content_hash(text),
        "published_at": scraped.date().isoformat(),
        "scraped_at": scraped.isoformat(),
        "reuse_reference": "test",
    }


def snapshot(tmp_path, name, records):
    path = tmp_path / name
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_merge_preserves_original(tmp_path):
    first = record()
    second = {**first, "reuse_reference": "new"}
    paths = [
        snapshot(tmp_path, "old.json", [first]),
        snapshot(tmp_path, "new.json", [second]),
    ]
    assert merge_records(paths) == {first["url"]: first}


def test_reject_conflicting_versions(tmp_path):
    with pytest.raises(ValueError, match="Conflicting versions"):
        merge_records(
            [snapshot(tmp_path, "a.json", [record(), record(text="Otro texto")])]
        )


def test_reject_hash_duplicate_other_url(tmp_path):
    with pytest.raises(ValueError, match="Same content"):
        merge_records(
            [
                snapshot(
                    tmp_path,
                    "a.json",
                    [
                        record(),
                        record(url="https://www.incibe.es/ciudadania/avisos/otro"),
                    ],
                )
            ]
        )


def test_reject_invalid_digest(tmp_path):
    with pytest.raises(ValueError, match="hash mismatch"):
        merge_records(
            [snapshot(tmp_path, "a.json", [{**record(), "content_hash": "invalid"}])]
        )


def test_manifest_requires_exact_coverage_and_hash():
    raw = record()
    records = {raw["url"]: raw}
    labels = {
        raw["url"]: {
            "content_hash": raw["content_hash"],
            "threat_type": "smishing",
            "secondary_threats": ["vishing"],
        }
    }
    assert prepare(records, labels, accept=False)[raw["url"]]["rag_allowed"] is False
    assert prepare(records, labels, accept=True)[raw["url"]]["rag_allowed"] is True
    with pytest.raises(ValueError, match="exactly"):
        prepare(records, {}, accept=True)
    labels[raw["url"]]["content_hash"] = "wrong"
    with pytest.raises(ValueError, match="changed"):
        prepare(records, labels, accept=True)
