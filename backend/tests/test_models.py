"""Comprueba que los modelos coinciden con las tablas del contrato (sin base de datos).
Checks that the models match the contract tables (no database needed).
"""

from sqlalchemy import Enum

import app.models  # noqa: F401
from app.db.base import Base

CONTRACT_TABLES = {
    "users",
    "devices",
    "pairings",
    "consents",
    "analyses",
    "temp_content",
    "analysis_attachments",
    "alerts",
    "unlocks",
    "indicators",
    "cases",
}

CONTRACT_PG_ENUMS = {
    "user_role",
    "channel",
    "input_type",
    "origin",
    "risk_level",
    "threat_type",
    "verdict_phase",
    "action",
    "alert_status",
    "unlock_status",
    "consent_type",
    "indicator_type",
    "case_status",
}


def test_all_contract_tables_exist():
    assert set(Base.metadata.tables) == CONTRACT_TABLES


def test_all_contract_pg_enums_exist():
    names = set()
    for table in Base.metadata.tables.values():
        for column in table.columns:
            column_type = getattr(column.type, "item_type", column.type)
            if isinstance(column_type, Enum):
                names.add(column_type.name)
    assert names == CONTRACT_PG_ENUMS


def test_enums_store_values_not_names():
    """ES: En la BD se guarda "red", no "RED". EN: The DB stores "red", not "RED"."""
    risk = Base.metadata.tables["analyses"].c.risk_level.type
    assert risk.enums == ["green", "amber", "red"]


def test_analyses_does_not_store_message_text():
    """ES: Privacidad: el texto vive solo en temp_content.
    EN: Privacy: text only lives in temp_content.
    """
    columns = set(Base.metadata.tables["analyses"].c.keys())
    assert not columns & {"text", "content", "anonymized_text", "message"}
