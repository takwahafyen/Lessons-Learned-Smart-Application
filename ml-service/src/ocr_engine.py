import re
from typing import Tuple, Optional, List
import cv2
import numpy as np
from PIL import Image
import pytesseract
from src.config import ROI_TOP, ROI_BOTTOM, ROI_LEFT, ROI_RIGHT, NUM_REGEX

class OCREngine:
    """
    Industrial Computer Vision & OCR processing engine.
    Applies multi-pass image preprocessing and dynamic region-of-interest extraction
    to reliably read noisy machine display panels.
    """

    @staticmethod
    def preprocess_image(cv_img: np.ndarray, scale: float = 2.0) -> np.ndarray:
        """
        Enhances text contrast and removes noise using bilateral filtering,
        morphological opening and adaptive Gaussian thresholding.
        """
        gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)
        if scale != 1.0:
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel, iterations=1)
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 9
        )

    @classmethod
    def extract_best_token(cls, pil_img: Image.Image) -> Tuple[Optional[str], Optional[float]]:
        """Extracts candidate error tokens scored by Tesseract confidence level."""
        data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
        best_token = None
        best_conf = -1.0

        for text, conf_val in zip(data.get('text', []), data.get('conf', [])):
            text_str = str(text).strip()
            try:
                conf = float(conf_val)
            except (ValueError, TypeError):
                continue

            if not text_str:
                continue

            cleaned = text_str.replace(' ', '').replace('—', '-').replace('–', '-')
            if NUM_REGEX.search(cleaned) and conf > best_conf and conf > 25.0:
                best_token = text_str
                best_conf = conf

        return best_token, (best_conf if best_token else None)

    @classmethod
    def process_frame(cls, pil_image: Image.Image, mirror: bool = True):
        """
        Processes an incoming frame with 3 concurrent strategies:
        1. Focused central ROI (Region of Interest)
        2. Full-frame Adaptive Threshold
        3. Otsu Global Binarization
        Returns: (token_for_model, display_token, details_text, annotated_image)
        """
        if pil_image is None:
            return None, None, "No image provided.", None

        img_np = np.array(pil_image.convert("RGB"))
        if mirror:
            img_np = cv2.flip(img_np, 1)

        h, w, _ = img_np.shape
        annotated_img = img_np.copy()

        # Define Region of Interest (ROI) bounding box
        y1, y2 = int(h * ROI_TOP), int(h * ROI_BOTTOM)
        x1, x2 = int(w * ROI_LEFT), int(w * ROI_RIGHT)
        y1, y2 = max(0, y1), min(h, y2)
        x1, x2 = max(0, x1), min(w, x2)
        cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 255, 0), 3)

        candidates = []

        # Strategy 1: Central ROI
        roi = img_np[y1:y2, x1:x2]
        if roi.size > 0:
            roi_pre = cls.preprocess_image(roi, scale=2.0)
            token, conf = cls.extract_best_token(Image.fromarray(roi_pre))
            if token:
                candidates.append((token, conf, "Central ROI"))

        # Strategy 2: Full-frame Adaptive Threshold
        full_pre = cls.preprocess_image(img_np, scale=1.5)
        token, conf = cls.extract_best_token(Image.fromarray(full_pre))
        if token:
            candidates.append((token, conf, "Adaptive Threshold"))

        # Strategy 3: Otsu Global Binarization
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        gray_up = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(gray_up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        token, conf = cls.extract_best_token(Image.fromarray(thresh))
        if token:
            candidates.append((token, conf, "Otsu Binarization"))

        if not candidates:
            fallback_text = pytesseract.image_to_string(Image.fromarray(full_pre)).strip()
            return None, None, f"No error token found. Raw OCR:\n{fallback_text}", Image.fromarray(annotated_img)

        # Select highest confidence match
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_token, best_conf, method = candidates[0]
        token_for_model = re.sub(r'[^A-Z0-9]', '', best_token.upper())

        info = f"Token detected: '{best_token}' (Confidence: {best_conf:.1f}%, Strategy: {method})"
        return token_for_model, best_token, info, Image.fromarray(annotated_img)
