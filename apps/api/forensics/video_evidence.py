"""
forensics/video_evidence.py — Automated video-frame evidence capture.

PRIVACY & SCOPE NOTICE:
This module performs presence detection and evidence capture ONLY.
It does NOT perform facial recognition, identity matching, or any lookup
against external databases. Automated identification of individuals from
captured frames is strictly out of scope and should not be added.
This capability requires law-enforcement legal authority, not a third-party
app, and carries serious misidentification/misuse risk.

This module stubs the WebRTC video capture by using a placeholder image path.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import cv2

logger = logging.getLogger(__name__)

# Path to the pre-trained Haar Cascade for frontal face detection
# OpenCV bundles this XML file. We locate it via cv2.data.haarcascades
CASCADE_PATH = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
_face_cascade = cv2.CascadeClassifier(CASCADE_PATH)


def process_test_frame(image_path: str, call_id: str) -> Optional[Dict[str, Any]]:
    """
    Process a video frame (stubbed via a test image path).
    
    1. Reads the image.
    2. Runs Haar Cascade to detect if at least one face is present.
    3. Computes SHA-256 hash of the image bytes for chain-of-custody.
    4. Returns metadata.

    Returns None if the image cannot be read.
    """
    if not os.path.exists(image_path):
        logger.warning(f"Video evidence stub: test image not found at {image_path}")
        return None

    try:
        # Read the raw bytes for hashing
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Compute SHA-256
        sha256_hash = hashlib.sha256(image_bytes).hexdigest()

        # Load image for OpenCV presence detection
        img = cv2.imread(image_path)
        if img is None:
            logger.warning(f"Video evidence stub: cv2 failed to read image at {image_path}")
            return None

        # Convert to grayscale for Haar Cascade
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect faces (presence only)
        faces = _face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        face_detected = len(faces) > 0
        
        logger.info(f"Video evidence processed: call_id={call_id} hash={sha256_hash[:8]}... face_detected={face_detected}")

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "call_id": call_id,
            "sha256_hash": sha256_hash,
            "face_detected": face_detected,
            "local_path": image_path,
        }

    except Exception as e:
        logger.error(f"Error processing video evidence frame: {e}", exc_info=True)
        return None
