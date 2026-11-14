import os
import math
from typing import Tuple, Dict, Any, Optional
import cv2
import numpy as np
from PIL import Image, ImageOps


class ImagePreprocessor:
    """Professional non-destructive image preprocessing for Arabic OCR and Vision AI."""

    @staticmethod
    def load_image_rgb(image_path: str) -> np.ndarray:
        """Load image safely preserving RGB channels, handling both images and PDFs."""
        if image_path.lower().endswith(".pdf"):
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(image_path)
            if len(pdf) == 0:
                raise ValueError("PDF document contains no pages.")
            page = pdf[0]
            pil_img = page.render(scale=2.0).to_pil()
        else:
            pil_img = Image.open(image_path)
            pil_img = ImageOps.exif_transpose(pil_img)

        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        return np.array(pil_img)

    @staticmethod
    def save_image(img_rgb: np.ndarray, output_path: str, quality: int = 95) -> None:
        """Save image in RGB format using PIL to prevent compression artifacts."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pil_img = Image.fromarray(img_rgb)
        pil_img.save(output_path, quality=quality)

    @classmethod
    def detect_skew_angle(cls, gray: np.ndarray) -> float:
        """Detect document skew angle in degrees using Hough Line Transform."""
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
        
        if lines is None or len(lines) == 0:
            return 0.0

        angles = []
        for line in lines:
            coords = line.flatten()
            if len(coords) < 4:
                continue
            x1, y1, x2, y2 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            # Filter near horizontal lines (-45 to 45 deg)
            if -45 < angle < 45:
                angles.append(angle)

        if not angles:
            return 0.0

        median_angle = float(np.median(angles))
        return median_angle

    @classmethod
    def rotate_image(cls, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by given angle without cropping corners."""
        if abs(angle) < 0.5:
            return image

        (h, w) = image.shape[:2]
        (cx, cy) = (w // 2, h // 2)

        M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])

        # Compute new bounding dimensions
        nw = int((h * sin) + (w * cos))
        nh = int((h * cos) + (w * sin))

        # Adjust transformation matrix
        M[0, 2] += (nw / 2) - cx
        M[1, 2] += (nh / 2) - cy

        return cv2.warpAffine(
            image, M, (nw, nh),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

    @classmethod
    def enhance_contrast(cls, img_rgb: np.ndarray) -> np.ndarray:
        """Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization) in LAB color space."""
        # Preserves color, diacritics, and thin Arabic pen strokes
        lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        enhanced_lab = cv2.merge((cl, a, b))
        return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)

    @classmethod
    def denoise_image(cls, img_rgb: np.ndarray) -> np.ndarray:
        """Lightweight edge-preserving denoising."""
        # Fast non-destructive bilateral filter for documents
        return cv2.bilateralFilter(img_rgb, d=5, sigmaColor=50, sigmaSpace=50)

    @classmethod
    def generate_preview(cls, input_path: str, preview_path: str, max_size: Tuple[int, int] = (1600, 1600)) -> Tuple[int, int]:
        """Generate high-quality preview for frontend display and return original dimensions."""
        if input_path.lower().endswith(".pdf"):
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(input_path)
            if len(pdf) == 0:
                raise ValueError("PDF document contains no pages.")
            img = pdf[0].render(scale=2.0).to_pil()
        else:
            img = Image.open(input_path)
            img = ImageOps.exif_transpose(img)

        orig_w, orig_h = img.size

        # Create copy and thumbnail
        preview_img = img.copy()
        preview_img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        os.makedirs(os.path.dirname(preview_path), exist_ok=True)
        if preview_img.mode != "RGB":
            preview_img = preview_img.convert("RGB")
        preview_img.save(preview_path, format="JPEG", quality=88, optimize=True)

        return orig_w, orig_h

    @classmethod
    def preprocess_for_ocr(cls, input_path: str, output_path: str) -> Dict[str, Any]:
        """Execute full preprocessing pipeline while maintaining image fidelity."""
        img_rgb = cls.load_image_rgb(input_path)
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        skew_angle = cls.detect_skew_angle(gray)
        processed = img_rgb
        applied_rotations = 0.0
        if abs(skew_angle) >= 0.5:
            processed = cls.rotate_image(processed, -skew_angle)
            applied_rotations = -skew_angle
        enhanced = cls.enhance_contrast(processed)
        final_img = cls.denoise_image(enhanced)
        cls.save_image(final_img, output_path)
        return {
            "original_width": img_rgb.shape[1],
            "original_height": img_rgb.shape[0],
            "skew_angle_detected": skew_angle,
            "skew_correction_applied": applied_rotations,
            "contrast_enhanced": True,
            "denoised": True,
            "processed_path": output_path,
        }
