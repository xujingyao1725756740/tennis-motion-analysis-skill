#!/usr/bin/env python3
"""Extract, phase-align, compare, score, and render tennis-motion analysis."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import pathlib
import statistics
import sys
from typing import Any, Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "models" / "pose_landmarker_full.task"
GROUND_PHASES = ["ready", "unit_turn", "racket_drop", "forward_swing", "contact", "finish"]
POSE_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer", "right_eye_inner", "right_eye",
    "right_eye_outer", "left_ear", "right_ear", "mouth_left", "mouth_right", "left_shoulder",
    "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist", "left_pinky",
    "right_pinky", "left_index", "right_index", "left_thumb", "right_thumb", "left_hip",
    "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle", "left_heel",
    "right_heel", "left_foot_index", "right_foot_index",
]


def load_json(path: str | pathlib.Path) -> Any:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def dump_json(path: str | pathlib.Path, data: Any) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def point(frame: dict[str, Any], name: str) -> tuple[float, float] | None:
    item = frame.get("landmarks", {}).get(name)
    if not item or item.get("visibility", 1.0) < 0.35:
        return None
    return float(item["x"]), float(item["y"])


def midpoint(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def joint_angle(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    ba, bc = (a[0] - b[0], a[1] - b[1]), (c[0] - b[0], c[1] - b[1])
    denom = math.hypot(*ba) * math.hypot(*bc)
    if denom < 1e-9:
        return float("nan")
    cosine = max(-1.0, min(1.0, (ba[0] * bc[0] + ba[1] * bc[1]) / denom))
    return math.degrees(math.acos(cosine))


def line_angle(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def wrapped_delta(a: float, b: float) -> float:
    return (a - b + 90) % 180 - 90


def metrics(frame: dict[str, Any], hand: str) -> dict[str, float | None]:
    p = {name: point(frame, name) for name in POSE_NAMES}
    out: dict[str, float | None] = {}
    for side in ("left", "right"):
        hip, knee, ankle = p[f"{side}_hip"], p[f"{side}_knee"], p[f"{side}_ankle"]
        out[f"{side}_knee_deg"] = joint_angle(hip, knee, ankle) if hip and knee and ankle else None
    shoulder, elbow, wrist = p[f"{hand}_shoulder"], p[f"{hand}_elbow"], p[f"{hand}_wrist"]
    out["dominant_elbow_deg"] = joint_angle(shoulder, elbow, wrist) if shoulder and elbow and wrist else None
    ls, rs, lh, rh = p["left_shoulder"], p["right_shoulder"], p["left_hip"], p["right_hip"]
    if ls and rs:
        shoulder_width = distance(ls, rs)
        out["shoulder_line_deg"] = line_angle(ls, rs)
    else:
        shoulder_width, out["shoulder_line_deg"] = 0.0, None
    out["hip_line_deg"] = line_angle(lh, rh) if lh and rh else None
    if out["shoulder_line_deg"] is not None and out["hip_line_deg"] is not None:
        out["shoulder_hip_separation_deg"] = wrapped_delta(
            float(out["shoulder_line_deg"]), float(out["hip_line_deg"])
        )
    else:
        out["shoulder_hip_separation_deg"] = None
    la, ra = p["left_ankle"], p["right_ankle"]
    out["base_width_shoulder"] = distance(la, ra) / shoulder_width if la and ra and shoulder_width else None
    if wrist and lh and rh and shoulder_width:
        hip_mid = midpoint(lh, rh)
        out["wrist_x_from_hip_shoulder"] = (wrist[0] - hip_mid[0]) / shoulder_width
        out["wrist_y_from_hip_shoulder"] = (wrist[1] - hip_mid[1]) / shoulder_width
    else:
        out["wrist_x_from_hip_shoulder"] = out["wrist_y_from_hip_shoulder"] = None
    return out


def nearest_frame(frames: list[dict[str, Any]], timestamp_ms: float) -> dict[str, Any]:
    valid = [frame for frame in frames if frame.get("landmarks")]
    if not valid:
        raise ValueError("pose JSON contains no detected frames")
    return min(valid, key=lambda frame: abs(float(frame["timestamp_ms"]) - timestamp_ms))


def median(values: Iterable[float | None]) -> float | None:
    usable = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return statistics.median(usable) if usable else None


def cmd_extract(args: argparse.Namespace) -> int:
    try:
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except ImportError as exc:
        raise SystemExit("Missing video runtime. Run scripts/bootstrap_runtime.py first.") from exc
    model = pathlib.Path(args.model)
    if not model.exists():
        raise SystemExit(f"Missing pose model: {model}. Run scripts/bootstrap_runtime.py first.")
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video: {args.video}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.45,
        min_pose_presence_confidence=0.45,
        min_tracking_confidence=0.45,
    )
    frames: list[dict[str, Any]] = []
    index = 0
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC) or (index * 1000 / max(fps, 1)))
            if index % args.every_n:
                index += 1
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms)
            landmark_map: dict[str, Any] = {}
            if result.pose_landmarks:
                for name, lm in zip(POSE_NAMES, result.pose_landmarks[0]):
                    landmark_map[name] = {
                        "x": round(float(lm.x), 7), "y": round(float(lm.y), 7),
                        "z": round(float(lm.z), 7), "visibility": round(float(lm.visibility or 0.0), 5),
                    }
            frames.append({"frame_index": index, "timestamp_ms": timestamp_ms, "landmarks": landmark_map})
            index += 1
    cap.release()
    dump_json(args.out, {
        "schema": "tennis-pose-v1", "source_video": str(pathlib.Path(args.video).resolve()),
        "fps": fps, "width": width, "height": height, "sample_every_n": args.every_n, "frames": frames,
    })
    detected = sum(bool(frame["landmarks"]) for frame in frames)
    print(f"Wrote {args.out}: {detected}/{len(frames)} sampled frames detected")
    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    if args.stroke not in {"forehand", "backhand"}:
        raise SystemExit("Automatic suggestions currently support forehand and backhand only.")
    data = load_json(args.pose_json)
    frames = [frame for frame in data["frames"] if point(frame, f"{args.hand}_wrist")]
    if len(frames) < 12:
        raise SystemExit("Too few detected wrist frames for phase suggestions.")
    speeds: list[tuple[float, int]] = []
    for previous, current in zip(frames, frames[1:]):
        dt = max(1.0, float(current["timestamp_ms"]) - float(previous["timestamp_ms"]))
        speeds.append((distance(point(previous, f"{args.hand}_wrist"), point(current, f"{args.hand}_wrist")) / dt, int(current["timestamp_ms"])))
    contact = max(speeds, key=lambda item: item[0])[1]
    start, end = int(frames[0]["timestamp_ms"]), int(frames[-1]["timestamp_ms"])
    span_before, span_after = max(300, contact - start), max(350, end - contact)
    phases = {
        "schema": "tennis-phases-v1", "stroke": args.stroke, "hand": args.hand,
        "provisional": True, "contact_confirmed": False,
        "notes": "Wrist-speed heuristic only. Visually confirm every marker, especially contact.",
        "phases_ms": {
            "ready": max(start, int(contact - span_before)),
            "unit_turn": max(start, int(contact - span_before * 0.66)),
            "racket_drop": max(start, int(contact - span_before * 0.34)),
            "forward_swing": max(start, int(contact - span_before * 0.16)),
            "contact": contact,
            "finish": min(end, int(contact + span_after * 0.72)),
        },
    }
    dump_json(args.out, phases)
    print(f"Wrote provisional markers to {args.out}; visually confirm contact before analysis.")
    return 0


def phase_metrics(pose: dict[str, Any], phases: dict[str, Any], hand: str) -> dict[str, dict[str, float | None]]:
    frames = pose["frames"]
    return {name: metrics(nearest_frame(frames, timestamp), hand) for name, timestamp in phases["phases_ms"].items()}


def cmd_compare(args: argparse.Namespace) -> int:
    user_pose, ref_pose = load_json(args.user_pose), load_json(args.reference_pose)
    user_phases, ref_phases = load_json(args.user_phases), load_json(args.reference_phases)
    for phase_file in (user_phases, ref_phases):
        missing = [name for name in GROUND_PHASES if name not in phase_file.get("phases_ms", {})]
        if missing:
            raise SystemExit("Missing phase markers: " + ", ".join(missing))
    user = phase_metrics(user_pose, user_phases, args.hand)
    ref = phase_metrics(ref_pose, ref_phases, args.reference_hand)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for phase in GROUND_PHASES:
        for metric_name in user[phase]:
            u, r = user[phase][metric_name], ref[phase][metric_name]
            rows.append({
                "phase": phase, "metric": metric_name, "player": u, "reference": r,
                "difference": (float(u) - float(r)) if u is not None and r is not None else None,
            })
    with (out_dir / "phase_metrics.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["phase", "metric", "player", "reference", "difference"])
        writer.writeheader(); writer.writerows(rows)
    summary = {
        "schema": "tennis-comparison-v1", "stroke": args.stroke,
        "contact_confirmed": bool(user_phases.get("contact_confirmed")) and bool(ref_phases.get("contact_confirmed")),
        "warning": "2D pose differences are coaching evidence, not proof of error or injury risk.",
        "player": user, "reference": ref, "rows": rows,
    }
    dump_json(out_dir / "comparison.json", summary)
    largest = sorted(
        (row for row in rows if row["difference"] is not None),
        key=lambda row: abs(float(row["difference"])), reverse=True,
    )[:12]
    html_rows = "".join(
        f"<tr><td>{row['phase']}</td><td>{row['metric']}</td><td>{row['player']:.2f}</td>"
        f"<td>{row['reference']:.2f}</td><td>{row['difference']:+.2f}</td></tr>" for row in largest
    )
    html = f"""<!doctype html><meta charset='utf-8'><title>Tennis motion comparison</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px;color:#17202a}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d5d8dc;padding:8px;text-align:right}}th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){{text-align:left}}.warn{{background:#fff4d6;padding:12px;border-left:4px solid #e0a800}}</style>
<h1>Tennis motion comparison</h1><p class='warn'>{summary['warning']}</p>
<p>Stroke: {args.stroke}. Contact confirmed in both clips: {summary['contact_confirmed']}.</p>
<h2>Largest measured 2D differences</h2><table><tr><th>Phase</th><th>Metric</th><th>Player</th><th>Reference</th><th>Difference</th></tr>{html_rows}</table>
<p>Review video evidence before turning these measurements into coaching conclusions.</p>"""
    (out_dir / "comparison.html").write_text(html, encoding="utf-8")
    print(f"Wrote comparison outputs to {out_dir}")
    return 0


def phase_map(phases: dict[str, Any], samples_per_segment: int) -> list[int]:
    values = [int(phases["phases_ms"][name]) for name in GROUND_PHASES]
    result: list[int] = []
    for start, end in zip(values, values[1:]):
        for index in range(samples_per_segment):
            result.append(round(start + (end - start) * index / samples_per_segment))
    result.append(values[-1])
    return result


def cmd_render(args: argparse.Namespace) -> int:
    try:
        import cv2
    except ImportError as exc:
        raise SystemExit("Missing video runtime. Run scripts/bootstrap_runtime.py first.") from exc
    user_cap, ref_cap = cv2.VideoCapture(args.user_video), cv2.VideoCapture(args.reference_video)
    if not user_cap.isOpened() or not ref_cap.isOpened():
        raise SystemExit("Could not open one or both videos.")
    user_times = phase_map(load_json(args.user_phases), args.samples_per_segment)
    ref_times = phase_map(load_json(args.reference_phases), args.samples_per_segment)
    canvas_h, panel_w = 720, 640
    writer = cv2.VideoWriter(args.out, cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (panel_w * 2, canvas_h))
    if not writer.isOpened():
        raise SystemExit(f"Could not create output video: {args.out}")
    for index, (user_ms, ref_ms) in enumerate(zip(user_times, ref_times)):
        panels = []
        for cap, timestamp, label in ((user_cap, user_ms, "PLAYER"), (ref_cap, ref_ms, "REFERENCE")):
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp)
            ok, frame = cap.read()
            if not ok:
                frame = cv2.imread(str(ROOT / "missing-frame.png")) if (ROOT / "missing-frame.png").exists() else None
            if frame is None:
                frame = __import__("numpy").zeros((canvas_h, panel_w, 3), dtype="uint8")
            scale = min(panel_w / frame.shape[1], canvas_h / frame.shape[0])
            resized = cv2.resize(frame, (int(frame.shape[1] * scale), int(frame.shape[0] * scale)))
            panel = __import__("numpy").zeros((canvas_h, panel_w, 3), dtype="uint8")
            y, x = (canvas_h - resized.shape[0]) // 2, (panel_w - resized.shape[1]) // 2
            panel[y:y+resized.shape[0], x:x+resized.shape[1]] = resized
            cv2.putText(panel, f"{label}  {timestamp/1000:.3f}s", (18, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
            panels.append(panel)
        writer.write(__import__("numpy").hstack(panels))
    writer.release(); user_cap.release(); ref_cap.release()
    print(f"Wrote phase-aligned video to {args.out}")
    return 0


def score_dimensions(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw = data.get("dimensions")
    if not isinstance(raw, list):
        raise SystemExit("Scorecard JSON must contain a 'dimensions' list.")
    dimensions: list[dict[str, Any]] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"Dimension {index} must be an object.")
        if item.get("score") is None:
            continue
        try:
            score = float(item["score"])
            weight = float(item.get("weight", 1.0))
        except (TypeError, ValueError) as exc:
            raise SystemExit(f"Dimension {index} has a non-numeric score or weight.") from exc
        if not 0 <= score <= 10:
            raise SystemExit(f"Dimension {index} score must be between 0 and 10.")
        if weight <= 0:
            raise SystemExit(f"Dimension {index} weight must be greater than zero.")
        label = str(item.get("label") or item.get("key") or f"Dimension {index}")
        dimensions.append({**item, "label": label, "score": score, "weight": weight})
    if not 3 <= len(dimensions) <= 10:
        raise SystemExit("A radar chart requires 3–10 scored dimensions; leave unsupported axes out.")
    return dimensions


def polar_point(center: float, radius: float, index: int, count: int) -> tuple[float, float]:
    angle = -math.pi / 2 + 2 * math.pi * index / count
    return center + radius * math.cos(angle), center + radius * math.sin(angle)


def svg_points(points: Iterable[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def cmd_scorecard(args: argparse.Namespace) -> int:
    data = load_json(args.scores_json)
    if not isinstance(data, dict):
        raise SystemExit("Scorecard JSON root must be an object.")
    dimensions = score_dimensions(data)
    total_weight = sum(float(item["weight"]) for item in dimensions)
    overall = round(
        sum(float(item["score"]) * float(item["weight"]) for item in dimensions) / total_weight,
        1,
    )
    count, center, radius, label_radius = len(dimensions), 300.0, 190.0, 236.0
    grid = []
    for ring in range(1, 6):
        ring_radius = radius * ring / 5
        grid.append(
            f'<polygon points="{svg_points(polar_point(center, ring_radius, i, count) for i in range(count))}" '
            f'fill="none" stroke="{args.grid}" stroke-width="1.5" opacity="0.8"/>'
        )
    axes = [
        f'<line x1="{center:.1f}" y1="{center:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
        f'stroke="{args.grid}" stroke-width="1.2" opacity="0.7"/>'
        for x, y in (polar_point(center, radius, i, count) for i in range(count))
    ]
    value_points = [
        polar_point(center, radius * float(item["score"]) / 10, i, count)
        for i, item in enumerate(dimensions)
    ]
    dots = [
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{args.accent}"/>'
        for x, y in value_points
    ]
    labels = []
    for index, item in enumerate(dimensions):
        x, y = polar_point(center, label_radius, index, count)
        if x < center - 25:
            anchor = "start"
        elif x > center + 25:
            anchor = "end"
        else:
            anchor = "middle"
        label = html.escape(str(item["label"]))
        labels.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" dominant-baseline="middle" '
            f'fill="{args.foreground}" font-family="sans-serif" font-size="19" font-weight="700">'
            f'{label} {float(item["score"]):.1f}</text>'
        )
    title = html.escape(str(data.get("title") or "Tennis motion scorecard"))
    svg = "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" role="img">',
        f'<title>{title}</title>',
        f'<rect width="600" height="600" fill="{args.background}"/>',
        f'<text x="30" y="38" fill="{args.foreground}" font-family="sans-serif" font-size="24" font-weight="700">{title}</text>',
        *grid,
        *axes,
        f'<polygon points="{svg_points(value_points)}" fill="{args.accent}" fill-opacity="0.24" '
        f'stroke="{args.accent}" stroke-width="4"/>',
        *dots,
        *labels,
        f'<circle cx="300" cy="300" r="58" fill="{args.background}" stroke="{args.accent}" stroke-width="3"/>',
        f'<text x="300" y="296" text-anchor="middle" fill="{args.accent}" font-family="sans-serif" font-size="40" font-weight="700">{overall:.1f}</text>',
        f'<text x="300" y="325" text-anchor="middle" fill="{args.foreground}" font-family="sans-serif" font-size="14">TRAINING SCORE</text>',
        '</svg>',
    ])
    out_svg = pathlib.Path(args.out_svg)
    out_svg.parent.mkdir(parents=True, exist_ok=True)
    out_svg.write_text(svg, encoding="utf-8")
    summary = {
        "schema": "tennis-scorecard-summary-v1",
        "title": data.get("title") or "Tennis motion scorecard",
        "overall": overall,
        "dimension_count": count,
        "chart": f"{count}-axis radar",
        "dimensions": dimensions,
        "level_estimate": data.get("level_estimate"),
        "warning": "Training score is not a professional percentile or formal competitive rating.",
    }
    if args.out_summary:
        dump_json(args.out_summary, summary)
    print(f"Wrote {count}-axis radar to {out_svg} (overall {overall:.1f}/10)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract", help="extract MediaPipe pose landmarks from video")
    extract.add_argument("video"); extract.add_argument("--out", required=True)
    extract.add_argument("--model", default=str(DEFAULT_MODEL)); extract.add_argument("--every-n", type=int, default=1)
    extract.set_defaults(func=cmd_extract)
    suggest = sub.add_parser("suggest-phases", help="create provisional groundstroke phase markers")
    suggest.add_argument("pose_json"); suggest.add_argument("--stroke", choices=["forehand", "backhand"], required=True)
    suggest.add_argument("--hand", choices=["left", "right"], required=True); suggest.add_argument("--out", required=True)
    suggest.set_defaults(func=cmd_suggest)
    compare = sub.add_parser("compare", help="compare two pose files at confirmed phase markers")
    compare.add_argument("user_pose"); compare.add_argument("reference_pose")
    compare.add_argument("--user-phases", required=True); compare.add_argument("--reference-phases", required=True)
    compare.add_argument("--stroke", choices=["forehand", "backhand"], required=True)
    compare.add_argument("--hand", choices=["left", "right"], required=True)
    compare.add_argument("--reference-hand", choices=["left", "right"], default="right")
    compare.add_argument("--out-dir", required=True); compare.set_defaults(func=cmd_compare)
    render = sub.add_parser("render", help="render a phase-aligned side-by-side comparison")
    render.add_argument("user_video"); render.add_argument("reference_video")
    render.add_argument("--user-phases", required=True); render.add_argument("--reference-phases", required=True)
    render.add_argument("--out", required=True); render.add_argument("--fps", type=float, default=20.0)
    render.add_argument("--samples-per-segment", type=int, default=20); render.set_defaults(func=cmd_render)
    scorecard = sub.add_parser("scorecard", help="generate an evidence-backed training radar chart")
    scorecard.add_argument("scores_json")
    scorecard.add_argument("--out-svg", required=True)
    scorecard.add_argument("--out-summary")
    scorecard.add_argument("--background", default="#071A16")
    scorecard.add_argument("--foreground", default="#F3F7E9")
    scorecard.add_argument("--accent", default="#D8FF3E")
    scorecard.add_argument("--grid", default="#4E6C63")
    scorecard.set_defaults(func=cmd_scorecard)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if getattr(args, "every_n", 1) < 1:
        raise SystemExit("--every-n must be at least 1")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
