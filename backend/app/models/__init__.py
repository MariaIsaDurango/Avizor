"""ES: Importa todos los modelos para que Alembic los vea en Base.metadata.
EN: Imports every model so Alembic sees them in Base.metadata.
"""

from app.models.alert import Alert, Unlock
from app.models.analysis import Analysis, AnalysisAttachment, TempContent
from app.models.indicator import Case, Indicator
from app.models.user import Consent, Device, Pairing, User

__all__ = [
    "Alert",
    "Analysis",
    "AnalysisAttachment",
    "Case",
    "Consent",
    "Device",
    "Indicator",
    "Pairing",
    "TempContent",
    "Unlock",
    "User",
]
