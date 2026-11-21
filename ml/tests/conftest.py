"""ES: Permite importar src.* desde ml/. EN: Allows importing src.* from ml/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
