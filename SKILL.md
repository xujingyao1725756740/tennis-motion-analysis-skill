---
name: tennis-motion-analysis
description: Analyze uploaded tennis videos frame by frame, confirm stroke phases, extract pose landmarks, compare phase-aligned technique with Djokovic or another player, score 6–8 training dimensions, create radar charts, give a carefully scoped NTRP-like level estimate, and produce HTML or Douyin/TikTok/Shorts coaching reports. Use for forehand, backhand, serve, volley, footwork, slow motion, joint angles, kinetic-chain sequencing, contact point, tennis level ratings, NTRP/UTR/WTN questions, professional-player comparisons, or tennis-analysis short videos from .mp4, .mov, .m4v, pose JSON, still frames, or match results.
---

# Tennis Motion Analysis

Analyze technique by stroke phase. Treat computer vision as measurement support, not as medical diagnosis, a formal competitive rating, or a requirement that the player copy one professional body shape.

## Workflow

1. Inspect every supplied video before judging technique.
   - Record stroke, handedness, camera class, frame rate, resolution, usable repetitions, ball/racket visibility, and occlusions.
   - Prefer 60–120 fps, fixed framing, full body plus racket, and at least five repetitions.
   - Preserve source files and write derived files to a separate output directory.
2. Build the reference set.
   - Use a primary reference with the same stroke, handedness or clearly mirrored handedness, stance, incoming-ball height, and same or adjacent camera class.
   - Use secondary rear or side references only to explain sequencing or spacing; do not combine their absolute 2D angles with the primary view.
   - If web research is needed, verify the current source and usage rights. Do not embed third-party footage in a public deliverable unless the user owns it or the license permits reuse.
3. Prepare the pose runtime only when needed:
   ```bash
   python3 scripts/bootstrap_runtime.py --check
   python3 scripts/bootstrap_runtime.py
   ```
4. Extract pose landmarks:
   ```bash
   .venv/bin/python scripts/tennis_motion.py extract player.mp4 --out player.pose.json
   .venv/bin/python scripts/tennis_motion.py extract reference.mp4 --out reference.pose.json
   ```
5. Generate provisional groundstroke markers:
   ```bash
   .venv/bin/python scripts/tennis_motion.py suggest-phases player.pose.json \
     --stroke forehand --hand right --out player.phases.json
   ```
6. Review every marker against the video. Manually confirm the contact timestamp before making contact-point or high-confidence sequencing claims. Read `references/analysis-protocol.md`.
7. Compare compatible phase-aligned data:
   ```bash
   .venv/bin/python scripts/tennis_motion.py compare player.pose.json reference.pose.json \
     --user-phases player.phases.json --reference-phases reference.phases.json \
     --stroke forehand --hand right --out-dir analysis
   ```
8. Render a synchronized comparison when both authorized source videos are available:
   ```bash
   .venv/bin/python scripts/tennis_motion.py render player.mp4 reference.mp4 \
     --user-phases player.phases.json --reference-phases reference.phases.json \
     --out analysis/phase-aligned-comparison.mp4
   ```
9. Score technique only when the evidence supports each axis. Use `references/scoring-ratings.md`, store the evidence and confidence beside every score, then generate the radar chart:
   ```bash
   .venv/bin/python scripts/tennis_motion.py scorecard scores.json \
     --out-svg analysis/radar.svg --out-summary analysis/scorecard.json
   ```
10. Write the coaching conclusion with `references/report-rubric.md`. If the user requests a social video, also read `references/publishing-workflow.md` and invoke the HyperFrames video skill for authoring and rendering.

## Guardrails

- Align by confirmed stroke phase, not raw frame number or wall-clock time.
- Normalize distances by shoulder or hip width. Never compare raw pixels across videos.
- Treat shoulder–hip separation and other image-plane angles as 2D proxies, not true axial rotation.
- Do not infer ball contact from a wrist-speed peak alone.
- Mark an unsupported score `N/A`; never turn missing evidence into zero.
- Keep the technique score separate from the player-level estimate.
- A single isolated stroke can support only a low-confidence, broad `NTRP-like` technique band. It cannot produce a formal NTRP, UTR, or WTN.
- Do not estimate UTR or WTN without match-result evidence from the relevant system.
- Separate observation, interpretation, and recommendation. Prioritize at most three changes and give one cue, drill, and measurable retest for each.
- Avoid injury diagnosis. Refer pain, instability, or suspected injury to a qualified coach or clinician.
- Record source URLs, creator, camera role, and rights status. For public publishing, replace restricted footage with authorized media, original diagrams, or source links.

## Resource routing

- Read `references/analysis-protocol.md` for phases, compatible views, multi-angle reference use, metrics, and confidence.
- Read `references/scoring-ratings.md` whenever the user requests scores, radar charts, NTRP, UTR, WTN, or a level estimate.
- Read `references/report-rubric.md` before producing the final coaching report.
- Read `references/publishing-workflow.md` for HTML reports, Douyin/TikTok/Shorts videos, source labels, safe zones, and export QA.
- Run `scripts/tennis_motion.py --help` for all commands and schemas.
- Run `scripts/bootstrap_runtime.py --check` to inspect local readiness without installing anything.
