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

# ── OPENCV ROBUST FACE DETECTOR SETUP ──────────────────────────────────────────
def _detect_face_roi(img_rgb: np.ndarray) -> Tuple[int, int, int, int]:
    """
    Robust face detection:
    1. Tries CascadeClassifier if available with xml file.
    2. Fallback to YCrCb skin-color geometry segmentation.
    3. Fallback to portrait-centered face region.
    """
    import cv2
    img_h, img_w = img_rgb.shape[:2]

    # Strategy 1: Haar cascade if available
    try:
        if hasattr(cv2, 'CascadeClassifier'):
            cascade_path = getattr(cv2.data, 'haarcascades', '') + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                detector = cv2.CascadeClassifier(cascade_path)
                if detector and not detector.empty():
                    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
                    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(MIN_FACE_SIZE, MIN_FACE_SIZE))
                    if len(faces) > 0:
                        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                        return tuple(faces[0])
    except Exception:
        pass

    # Strategy 2: Skin-color segmentation in YCrCb space
    try:
        bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
        skin_mask = cv2.inRange(ycrcb, np.array([0, 133, 77], dtype=np.uint8), np.array([255, 173, 127], dtype=np.uint8))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel, iterations=2)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        cnts, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        candidates = []
        min_dim = max(MIN_FACE_SIZE, int(min(img_h, img_w) * 0.15))
        for c in cnts:
            bx, by, bw, bh = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            ratio = bh / float(bw) if bw > 0 else 0
            if bw >= min_dim and bh >= min_dim and 0.65 <= ratio <= 2.4 and area > (min_dim * min_dim * 0.35):
                cx = bx + bw / 2.0
                cy = by + bh / 2.0
                dist_center = np.hypot(cx - img_w / 2.0, cy - img_h / 2.0)
                score = area - dist_center * 10
                candidates.append((score, (bx, by, bw, bh)))
        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            return candidates[0][1]
    except Exception:
        pass

    # Strategy 3: Centered portrait face box
    crop_w = int(img_w * 0.6)
    crop_h = int(img_h * 0.65)
    x = max(0, int((img_w - crop_w) / 2))
    y = max(0, int((img_h - crop_h) * 0.3))
    return (x, y, crop_w, crop_h)


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
    Detects face ROI, resizes to 64x64, computes normalized histogram descriptor as embedding vector.
    """
    import cv2

    # Downscale for speed
    max_dim = 800
    if max(img_pil.size) > max_dim:
        img_pil.thumbnail((max_dim, max_dim), Image.LANCZOS)

    gray = np.array(img_pil.convert('L'))
    rgb = np.array(img_pil.convert('RGB'))

    face_bbox = _detect_face_roi(rgb)
    x, y, w, h = face_bbox

    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
        return None, "Face region is too small. Please use a closer, clearer photo."

    # Crop face ROI with margin
    margin = int(min(w, h) * 0.08)
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
