import re
import ast
import logging
from typing import Tuple
import joblib
from src.config import MODEL_PATH

logger = logging.getLogger(__name__)

class ErrorPredictor:
    """
    NLP & Classification Engine.
    Loads the trained vectorizer and scikit-learn model, then transforms normalized
    tokens into diagnostic outputs (Root Cause + Standardized Solution).
    """

    def __init__(self):
        self.vectorizer = None
        self.model = None
        self.load_model()

    def load_model(self):
        try:
            if MODEL_PATH.exists():
                self.vectorizer, self.model = joblib.load(MODEL_PATH)
                logger.info("Successfully loaded ML model & vectorizer.")
            else:
                logger.warning(f"Model file not found at {MODEL_PATH}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.vectorizer = None
            self.model = None

    def parse_prediction(self, raw_pred) -> Tuple[str, str]:
        """
        Decodes model predictions into (cause, solution) regardless of internal target serialization.
        """
        default = ("Cause non spécifiée", "Solution non spécifiée")

        if isinstance(raw_pred, (list, tuple)) and len(raw_pred) >= 2:
            return str(raw_pred[0]), str(raw_pred[1])

        if hasattr(raw_pred, "tolist"):
            items = raw_pred.tolist()
            if isinstance(items, (list, tuple)) and len(items) >= 2:
                return str(items[0]), str(items[1])

        s = str(raw_pred).strip()

        # Extract items within single quotes
        single_quoted = re.findall(r"'([^']*)'", s)
        if len(single_quoted) >= 2:
            return single_quoted[0], single_quoted[1]

        # Extract items within double quotes
        double_quoted = re.findall(r'"([^"]*)"', s)
        if len(double_quoted) >= 2:
            return double_quoted[0], double_quoted[1]

        try:
            val = ast.literal_eval(s)
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                return str(val[0]), str(val[1])
        except Exception:
            pass

        return default[0], s

    def predict(self, normalized_code: str) -> Tuple[str, str]:
        if not self.model or not self.vectorizer:
            raise RuntimeError("Model or Vectorizer is not loaded.")

        vect = self.vectorizer.transform([normalized_code])
        raw_pred = self.model.predict(vect)[0]
        return self.parse_prediction(raw_pred)
