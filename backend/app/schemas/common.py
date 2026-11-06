"""Base común para todos los schemas del contrato.
Common base for all contract schemas.
"""

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """ES: Ignora campos desconocidos (regla del contrato) y valida al asignar.
    EN: Ignores unknown fields (contract rule) and validates on assignment.
    """

    model_config = ConfigDict(extra="ignore", validate_assignment=True)
