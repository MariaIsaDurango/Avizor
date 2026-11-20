import sys
from pathlib import Path

# Make `src.*` importable when pytest runs from the project root.
_ML_ROOT = Path(__file__).resolve().parents[1]
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))
