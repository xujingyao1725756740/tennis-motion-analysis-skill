# Analysis protocol

## Phase model

Use these six ordered anchors for groundstrokes:

1. `ready`: split-step recovery or stable preparation before the unit turn.
2. `unit_turn`: shoulders have substantially turned and both hands still organize the racket when visible.
3. `racket_drop`: lowest practical preparation point before forward acceleration; infer from the wrist only when the racket is not detected and lower confidence.
4. `forward_swing`: forward acceleration has clearly begun.
5. `contact`: ball-racket impact. Confirm visually; never claim exact contact from pose landmarks alone.
6. `finish`: major deceleration ends and the body reaches a stable follow-through.

For serves, use `ready`, `trophy`, `leg_drive`, `racket_drop`, `contact`, and `finish`. Mark serve phases manually; the current heuristic phase suggester is for groundstrokes.

## Reference-set design

Classify each view as rear, rear-oblique, side, front-oblique, or front.

- Primary reference: use the same class or an adjacent oblique class, comparable stroke intent, stance, incoming-ball height, and movement direction. Use it for phase-aligned measurements.
- Secondary reference: use rear or side footage to explain rotation order, recovery, spacing, or racket path. Label it `angle reset` and compare patterns, not absolute degrees.
- Handedness: mirror the visual concept explicitly when needed; never silently relabel left and right.
- Professional reference: compare repeatable principles and sequencing, not body-specific cosmetic positions.

Reject precise angle comparison when:

- the measured joint is hidden for more than 20% of the phase;
- the camera moves substantially;
- video is below 24 fps near contact;
- the subject occupies less than roughly one quarter of frame height;
- the reference uses a materially different stroke, stance, incoming-ball height, or movement pattern.

## Repetition and contact rules

- One stroke can reveal a visible pattern but cannot establish consistency.
- Use at least five similar repetitions for repeatability claims and ten when estimating a recreational level.
- Confirm contact visually in the original frames. Record a timestamp or frame interval when impact falls between frames.
- If the ball or racket is hidden, call it a contact proxy and lower confidence.

## Core metrics

- Knee flexion: hip-knee-ankle angle on both sides.
- Elbow structure: shoulder-elbow-wrist angle on the dominant side.
- Shoulder line: image-plane angle between shoulders.
- Hip line: image-plane angle between hips.
- Shoulder-hip separation: wrapped difference between shoulder and hip line angles. Treat as a 2D proxy.
- Head stability: nose displacement relative to shoulder width across the forward swing.
- Base width: ankle separation divided by shoulder width.
- Contact proxy: dominant wrist location relative to mid-hip and shoulder width, only after visual contact review.
- Sequencing proxy: timing of hip-line, shoulder-line, elbow, and wrist changes. Do not call this a complete kinetic chain without racket and ball evidence.

## Confidence

Assign confidence per claim:

- High: same view and stroke, 60+ fps, strong visibility, confirmed contact, and a repeatable pattern across at least five strokes.
- Medium: compatible view, 30+ fps, confirmed contact, and only minor occlusion or perspective uncertainty.
- Low: one repetition, mismatched view, low fps, major occlusion, unconfirmed contact, or wrist used as a racket proxy.

Do not average confidence across unrelated claims. Put the limiting evidence beside every low-confidence conclusion.
