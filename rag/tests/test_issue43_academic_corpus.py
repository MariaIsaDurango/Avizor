"""The academic decision is explicit and separate from copyright authorization."""

import json
import sys
from datetime import UTC, datetime, timedelta

import pytest

from rag.scripts.prepare_issue43_corpus import main
from rag.src.ingestion.cleaner import content_hash


def test_manifest_draft_and_team_decision(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    raw_path = tmp_path / "rag/data/raw/incibe_content.json"
    raw_path.parent.mkdir(parents=True)
    text = "Texto ficticio de prueba, no constituye un aviso oficial real."
    url = "https://www.incibe.es/ciudadania/avisos/fixture"
    scraped = datetime.now(UTC) - timedelta(days=1)
    raw = [
        {
            "source": "incibe",
            "url": url,
            "title": "Fixture",
            "text": text,
            "content_hash": content_hash(text),
            "published_at": scraped.date().isoformat(),
            "scraped_at": scraped.isoformat(),
            "reuse_reference": "Fixture only",
        }
    ]
    original = json.dumps(raw)
    raw_path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["prepare", "--output", "draft.json"])
    main()
    draft = json.loads((tmp_path / "draft.json").read_text())
    assert draft[url]["rag_allowed"] is False
    assert draft[url]["classification_status"] == "preliminary_title_based"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prepare",
            "--labels",
            "draft.json",
            "--accept-team-policy",
            "--output",
            "approved.json",
        ],
    )
    main()
    final = json.loads((tmp_path / "approved.json").read_text())
    assert final[url]["rag_allowed"] is True
    assert "no autorización expresa" in final[url]["reference"]
    assert raw_path.read_text() == original
    with pytest.raises(SystemExit):
        main()
