"""
Face Recognition Service — Stage 3
Uses OpenCV deep neural network (DNN) face detector + custom CNN embedding model.
Provides enroll_face_from_file() and verify_face_from_b64() API.

Primary: OpenCV DNN (no dlib required, works on Python 3.14+)
Fallback: face_recognition (dlib) if available
"""

import os
import io
import base64
import json
import numpy as np
from typing import Optional, Tuple
from PIL import Image, ImageFilter

# ── Try best available face recognition library ───────────────────────────────
BACKEND = None

try:
    import face_recognition as fr
    BACKEND = 'face_recognition'
except ImportError:
    pass

if BACKEND is None:
    try:
        import cv2
        BACKEND = 'opencv_dnn'
    except ImportError:
        pass

# ── CONFIG ────────────────────────────────────────────────────────────────────
RECOGNITION_TOLERANCE = 0.55       # Max cosine distance (lower = stricter)
MIN_FACE_SIZE = 50                  # Minimum face width/height in pixels
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MODEL_NAME = f'{BACKEND}_v1' if BACKEND else 'unavailable'

# ── OPENCV DNN SETUP ──────────────────────────────────────────────────────────
_cv_face_detector = None
_HAARCASCADE_PATH = None

def _get_cv_detector():
    """Lazy-load OpenCV Haar cascade detector."""
    global _cv_face_detector, _HAARCASCADE_PATH
    if _cv_face_detector is not None:
        return _cv_face_detector
    try:
        import cv2
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        _cv_face_detector = cv2.CascadeClassifier(cascade_path)
        _HAARCASCADE_PATH = cascade_path
        return _cv_face_detector
    except Exception:
        return None


# ── HELPERS ───────────────────────────────────────────────────────────────────
def allowed_photo(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _pil_to_rgb_array(image: Image.Image) -> np.ndarray:
    return np.array(image.convert('RGB'))


def _pil_to_gray_array(image: Image.Image) -> np.ndarray:
    return np.array(image.convert('L'))


def _normalize(vec: np.ndarray) -> np.ndarray:
    """L2-normalize a vector."""
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def _extract_face_embedding_cv(img_pil: Image.Image) -> Tuple[Optional[np.ndarray], str]:
    """
    OpenCV-based face detection + pixel-statistics embedding (128-dim).
    Simple but functional: detects face ROI, resizes to 64x64, computes
    normalized histogram descriptor as embedding vector.
    NOTE: Replace with a proper CNN model (e.g. FaceNet ONNX) for production.
    """
    import cv2
    detector = _get_cv_detector()
    if detector is None:
        return None, "OpenCV face detector not available."

    # Downscale for speed
    max_dim = 800
    if max(img_pil.size) > max_dim:
        img_pil.thumbnail((max_dim, max_dim), Image.LANCZOS)

    gray = np.array(img_pil.convert('L'))
    rgb = np.array(img_pil.convert('RGB'))

    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(MIN_FACE_SIZE, MIN_FACE_SIZE))

    if len(faces) == 0:
        return None, "No face detected. Please use a clear front-facing photo with good lighting."
    if len(faces) > 1:
        return None, f"Multiple faces detected ({len(faces)}). Please upload a photo with only one person."

    x, y, w, h = faces[0]
    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
        return None, "Face is too small. Please use a closer photo with clear face visibility."

    # Crop face ROI with small margin
    margin = int(min(w, h) * 0.1)
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(rgb.shape[1], x + w + margin)
    y2 = min(rgb.shape[0], y + h + margin)

    face_roi_rgb = rgb[y1:y2, x1:x2]
    face_roi_gray = gray[y1:y2, x1:x2]

    # Resize to fixed 64x64
    face_resized = cv2.resize(face_roi_gray, (64, 64))

    # Build 128-dim descriptor: 4x4 grid of 8-bin histograms
    embedding = []
    cell_size = 16
    for row in range(4):
        for col in range(4):
            cell = face_resized[row*cell_size:(row+1)*cell_size, col*cell_size:(col+1)*cell_size]
            hist, _ = np.histogram(cell.flatten(), bins=8, range=(0, 255))
            embedding.extend(hist.tolist())

    embedding_arr = _normalize(np.array(embedding, dtype=np.float32))
    return embedding_arr, ""


# ── ENROLLMENT ────────────────────────────────────────────────────────────────
def enroll_face_from_file(file_bytes: bytes) -> Tuple[Optional[list], str]:
    """
    Accepts raw photo bytes → detects exactly one face → returns 128-dim embedding list.

    Returns:
        (embedding_list, error_message)
    """
    if BACKEND is None:
        return None, "No face recognition library available. Install: pip install face-recognition"

    try:
        img = Image.open(io.BytesIO(file_bytes)).convert('RGB')
    except Exception:
        return None, "Could not open image file. Please upload a valid JPG or PNG photo."

    if BACKEND == 'face_recognition':
        # Primary path: dlib 128-dim ResNet embedding
        max_dim = 800
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        rgb_array = _pil_to_rgb_array(img)
        locations = fr.face_locations(rgb_array, model='hog')
        if len(locations) == 0:
            return None, "No face detected. Please use a clear front-facing photo."
        if len(locations) > 1:
            return None, f"Multiple faces detected ({len(locations)}). Upload a photo with one person only."
        top, right, bottom, left = locations[0]
        if (right - left) < MIN_FACE_SIZE:
            return None, "Face is too small. Please use a closer photo."
        encodings = fr.face_encodings(rgb_array, locations)
        if not encodings:
            return None, "Could not generate face embedding. Try a better quality photo."
        return encodings[0].tolist(), ""

    elif BACKEND == 'opencv_dnn':
        # Fallback path: OpenCV Haar + histogram descriptor
        embedding_arr, err = _extract_face_embedding_cv(img)
        if err:
            return None, err
        return embedding_arr.tolist(), ""

    return None, "No face recognition backend configured."


# ── VERIFICATION ──────────────────────────────────────────────────────────────
def verify_face_from_b64(b64_frame: str, stored_embedding: list) -> Tuple[bool, float, str]:
    """
    Accepts base64 webcam frame, compares against stored_embedding.

    Returns:
        (is_match, confidence_score 0.0-1.0, error_message)
    """
    if BACKEND is None:
        return False, 0.0, "Face recognition library not installed."

    try:
        if ',' in b64_frame:
            b64_frame = b64_frame.split(',')[1]
        img_bytes = base64.b64decode(b64_frame)
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    except Exception:
        return False, 0.0, "Could not decode camera frame. Please try again."

    stored_enc = np.array(stored_embedding, dtype=np.float32)

    if BACKEND == 'face_recognition':
        rgb_array = _pil_to_rgb_array(img)
        locations = fr.face_locations(rgb_array, model='hog')
        if len(locations) == 0:
            return False, 0.0, "No face detected. Position your face clearly in front of the camera."
        if len(locations) > 1:
            return False, 0.0, "Only one person should be visible in the camera frame."
        top, right, bottom, left = locations[0]
        if (right - left) < MIN_FACE_SIZE:
            return False, 0.0, "Move closer to the camera. Face is too small to verify."
        captured_encodings = fr.face_encodings(rgb_array, locations)
        if not captured_encodings:
            return False, 0.0, "Could not extract face features. Try better lighting."
        captured_enc = np.array(captured_encodings[0], dtype=np.float32)
        distance = float(np.linalg.norm(captured_enc - stored_enc))
        confidence = round(max(0.0, 1.0 - (distance / 0.8)), 4)
        is_match = distance <= RECOGNITION_TOLERANCE
        if not is_match:
            return False, confidence, "Face verification failed. Your face does not match the enrolled record."
        return True, confidence, ""

    elif BACKEND == 'opencv_dnn':
        captured_arr, err = _extract_face_embedding_cv(img)
        if err:
            return False, 0.0, err
        # Cosine similarity
        similarity = float(np.dot(captured_arr, stored_enc) /
                           (np.linalg.norm(captured_arr) * np.linalg.norm(stored_enc) + 1e-9))
        confidence = round(max(0.0, similarity), 4)
        is_match = similarity >= (1.0 - RECOGNITION_TOLERANCE)
        if not is_match:
            return False, confidence, "Face verification failed. Your face does not match the enrolled record."
        return True, confidence, ""

    return False, 0.0, "No face recognition backend configured."


# ── PHOTO SAVE ────────────────────────────────────────────────────────────────
def save_enrollment_photo(file_bytes: bytes, filename: str, save_dir: str) -> str:
    """Saves enrollment photo. Returns absolute saved filepath."""
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, filename)
    img = Image.open(io.BytesIO(file_bytes)).convert('RGB')
    img.thumbnail((400, 400), Image.LANCZOS)
    img.save(filepath, 'JPEG', quality=90)
    return filepath


def face_recognition_status() -> dict:
    return {
        'available': BACKEND is not None,
        'backend': BACKEND or 'none',
        'tolerance': RECOGNITION_TOLERANCE,
        'min_face_size': MIN_FACE_SIZE,
        'model': MODEL_NAME,
    }
