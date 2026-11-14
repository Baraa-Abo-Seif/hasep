import os
import numpy as np
import pytest
from backend.app.image_processing.preprocessor import ImagePreprocessor


def test_image_preprocessing_enhancement():
    # Create test RGB image
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    # Draw some text-like lines
    img[100:110, 50:250] = 200
    img[150:160, 50:250] = 180

    # Test contrast enhancement
    enhanced = ImagePreprocessor.enhance_contrast(img)
    assert enhanced.shape == img.shape
    assert enhanced.dtype == np.uint8

    # Test denoising
    denoised = ImagePreprocessor.denoise_image(enhanced)
    assert denoised.shape == img.shape


def test_image_rotation():
    img = np.ones((200, 100, 3), dtype=np.uint8) * 128
    rotated = ImagePreprocessor.rotate_image(img, 15.0)
    assert rotated is not None
    # Dimension increases due to corner non-clipping
    assert rotated.shape[0] >= 200
    assert rotated.shape[1] >= 100


def test_preview_generation(tmp_path):
    test_file = str(tmp_path / "test_orig.jpg")
    preview_file = str(tmp_path / "test_preview.jpg")

    dummy_img = np.ones((1000, 800, 3), dtype=np.uint8) * 200
    ImagePreprocessor.save_image(dummy_img, test_file)

    orig_w, orig_h = ImagePreprocessor.generate_preview(test_file, preview_file, max_size=(400, 400))
    assert orig_w == 800
    assert orig_h == 1000
    assert os.path.exists(preview_file)
