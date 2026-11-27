from __future__ import annotations

import time
from pathlib import Path
from typing import Generator, List, Optional, Tuple

import cv2
import numpy as np

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class DynamicFpsController:
    """
    Motion-aware dynamic frame rate controller for low-power edge boxes.
    Downscales frame to 96x96 grayscale to measure inter-frame motion ratio:
    - Static scene -> throttles to `idle_fps` (e.g. 0.5 FPS)
    - Motion detected -> boosts immediately to `active_fps` (e.g. 8~15 FPS) for a 3-second hold window.
    """

    def __init__(
        self,
        enabled: bool = True,
        idle_fps: float = 0.5,
        active_fps: float = 8.0,
        motion_pixel_threshold: float = 0.015,
    ) -> None:
        self.enabled = enabled
        self.idle_fps = max(0.1, idle_fps)
        self.active_fps = max(self.idle_fps, active_fps)
        self.motion_pixel_threshold = motion_pixel_threshold
        self._prev_small: Optional[np.ndarray] = None
        self._last_infer_ts: float = 0.0
        self._active_until_ts: float = 0.0
        self.total_frames_seen: int = 0
        self.frames_inferred: int = 0
        self.frames_skipped: int = 0

    def should_process(self, frame_bgr: np.ndarray, now_ts: Optional[float] = None) -> Tuple[bool, float, float]:
        """Returns (should_infer, target_fps, motion_ratio)."""
        now = now_ts if now_ts is not None else time.monotonic()
        self.total_frames_seen += 1

        if not self.enabled:
            self.frames_inferred += 1
            self._last_infer_ts = now
            return True, self.active_fps, 1.0

        gray = cv2.cvtColor(cv2.resize(frame_bgr, (96, 96)), cv2.COLOR_BGR2GRAY)
        motion_ratio = 1.0
        if self._prev_small is not None:
            diff = cv2.absdiff(gray, self._prev_small)
            motion_ratio = float(np.count_nonzero(diff > 18)) / float(96 * 96)
            if motion_ratio >= self.motion_pixel_threshold:
                self._active_until_ts = now + 3.0
        else:
            self._active_until_ts = now + 1.0

        self._prev_small = gray
        target_fps = self.active_fps if now <= self._active_until_ts else self.idle_fps
        min_interval = 1.0 / max(0.1, target_fps)

        if (now - self._last_infer_ts) >= min_interval or self.frames_inferred == 0:
            self._last_infer_ts = now
            self.frames_inferred += 1
            return True, target_fps, round(motion_ratio, 4)

        self.frames_skipped += 1
        return False, target_fps, round(motion_ratio, 4)


def iter_frames_from_source(
    source: str, base_dir: Path, max_frames: Optional[int] = None
) -> Generator[Tuple[str, np.ndarray], None, None]:
    """
    Unified frame iterator supporting:
      - Local image file or directory of snapshots
      - USB webcam index ("0", "1")
      - RTSP / RTMP / HTTP stream or local MP4 video file
    """
    if not source:
        return

    resolved = Path(source)
    if not resolved.is_absolute() and not source.startswith(("rtsp://", "rtmp://", "http://", "https://")) and not source.isdigit():
        resolved = (base_dir / source).resolve()

    count = 0
    if resolved.exists() and resolved.is_file() and resolved.suffix.lower() in IMAGE_EXTS:
        img = cv2.imread(str(resolved))
        if img is not None:
            yield resolved.name, img
        return

    if resolved.exists() and resolved.is_dir():
        files: List[Path] = sorted(
            [p for p in resolved.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
        )
        for p in files:
            img = cv2.imread(str(p))
            if img is None:
                continue
            yield p.name, img
            count += 1
            if max_frames and count >= max_frames:
                return
        return

    cap_arg = int(source) if source.isdigit() else (str(resolved) if resolved.exists() else source)
    cap = cv2.VideoCapture(cap_arg)
    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            count += 1
            yield f"frame_{count:06d}", frame
            if max_frames and count >= max_frames:
                break
    finally:
        cap.release()
