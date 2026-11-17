import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "erreur_model_numero.pkl"

# Region of Interest (ROI) relative boundaries
ROI_TOP = 0.35
ROI_BOTTOM = 0.65
ROI_LEFT = 0.25
ROI_RIGHT = 0.75

# Regex to match industrial error codes (e.g. E-102, ERR504, 1204)
NUM_REGEX = re.compile(r'[A-Z]?\s*-?\s*\d{2,6}', re.IGNORECASE)
