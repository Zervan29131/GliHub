from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple


def point_in_polygon(px: float, py: float, polygon: Sequence[Sequence[float]]) -> bool:
    """Ray-casting point-in-polygon check. Empty or <3 vertex polygon means full-frame pass."""
    n = len(polygon)
    if n < 3:
        return True
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = float(polygon[i][0]), float(polygon[i][1])
        xj, yj = float(polygon[j][0]), float(polygon[j][1])
        intersect = ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def normalize_polygon(
    polygon: Sequence[Sequence[float]], img_w: int, img_h: int
) -> List[Tuple[float, float]]:
    """Accepts either normalized [0..1] or pixel coordinates and returns pixel vertices."""
    if not polygon:
        return []
    max_coord = max(max(abs(float(pt[0])), abs(float(pt[1]))) for pt in polygon)
    if max_coord <= 1.05:
        return [(float(pt[0]) * img_w, float(pt[1]) * img_h) for pt in polygon]
    return [(float(pt[0]), float(pt[1])) for pt in polygon]


def filter_detections_by_roi(
    detections: List[Dict[str, Any]],
    polygon: Sequence[Sequence[float]],
    img_w: int,
    img_h: int,
    anchor_mode: str = "foot_or_center",
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Filters detections against polygon ROI.
    Uses bottom-center ('foot point') for persons/poses so fence-stepping is accurate,
    and bbox center for general objects/OBB/seg.
    Returns (kept_detections, filtered_out_count).
    """
    if not polygon or len(polygon) < 3:
        for d in detections:
            d["in_roi"] = True
        return detections, 0

    pix_poly = normalize_polygon(polygon, img_w, img_h)
    kept: List[Dict[str, Any]] = []
    dropped = 0

    for det in detections:
        bbox = det.get("bbox") or [0.0, 0.0, 0.0, 0.0]
        x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        cls_name = str(det.get("class_name", "")).lower()
        if anchor_mode == "foot_or_center" and cls_name in (
            "person",
            "no_helmet",
            "with_helmet",
            "worker",
            "fall_risk",
        ):
            ax = 0.5 * (x1 + x2)
            ay = y1 + 0.88 * (y2 - y1)
        else:
            ax = 0.5 * (x1 + x2)
            ay = 0.5 * (y1 + y2)

        if point_in_polygon(ax, ay, pix_poly):
            det["in_roi"] = True
            kept.append(det)
        else:
            dropped += 1

    return kept, dropped


def couple_person_and_helmet(
    person_dets: List[Dict[str, Any]],
    helmet_dets: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Spatial coupling between general person detections (YOLO26n) and custom helmet detections
    (YOLOv5 best.int8.onnx `With Helmet`):
    - Checks whether each person's upper-head region overlaps any `With Helmet` box.
    - Emits explicit `NO_HELMET` violation items for unprotected workers and keeps `WITH_HELMET`
      compliant markers so safety recheck & VLM review get ground-truth structured context.
    """
    enriched: List[Dict[str, Any]] = []
    used_helmets = set()

    for p in person_dets:
        if str(p.get("class_name", "")).lower() != "person":
            enriched.append(p)
            continue
        px1, py1, px2, py2 = [float(v) for v in p["bbox"]]
        pw = max(1.0, px2 - px1)
        ph = max(1.0, py2 - py1)
        # Upper 45% of person box (expanded slightly upwards for helmet crown)
        hx1 = px1 - 0.12 * pw
        hy1 = max(0.0, py1 - 0.15 * ph)
        hx2 = px2 + 0.12 * pw
        hy2 = py1 + 0.45 * ph

        matched_helmet = None
        for idx, h in enumerate(helmet_dets):
            bx1, by1, bx2, by2 = [float(v) for v in h["bbox"]]
            cx = 0.5 * (bx1 + bx2)
            cy = 0.5 * (by1 + by2)
            ix1, iy1 = max(hx1, bx1), max(hy1, by1)
            ix2, iy2 = min(hx2, bx2), min(hy2, by2)
            inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
            h_area = max(1.0, (bx2 - bx1) * (by2 - by1))
            if (hx1 <= cx <= hx2 and hy1 <= cy <= hy2) or (inter / h_area >= 0.25):
                matched_helmet = h
                used_helmets.add(idx)
                break

        if matched_helmet is not None:
            compliant = dict(p)
            compliant["class_name"] = "with_helmet"
            compliant["label_cn"] = "规范佩戴安全帽"
            compliant["is_violation"] = False
            compliant["helmet_conf"] = round(float(matched_helmet.get("confidence", 0.0)), 4)
            enriched.append(compliant)
        else:
            violation = dict(p)
            violation["class_name"] = "no_helmet"
            violation["label_cn"] = "未佩戴安全帽"
            violation["is_violation"] = True
            violation["risk_level"] = "HIGH"
            enriched.append(violation)

    for idx, h in enumerate(helmet_dets):
        if idx not in used_helmets:
            standalone = dict(h)
            standalone["class_name"] = "with_helmet"
            standalone["label_cn"] = "规范佩戴安全帽"
            standalone["is_violation"] = False
            enriched.append(standalone)

    return enriched
