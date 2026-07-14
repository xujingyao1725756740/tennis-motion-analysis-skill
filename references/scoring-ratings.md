# Scoring and rating rules

## Training score versus player rating

Keep these separate:

- Training score: a 0–10 coaching-priority score for visible technique dimensions in the supplied footage.
- Player-level estimate: a broad description of overall recreational playing ability, which needs strokes, movement, consistency, point play, and preferably match results.

Never convert one into the other mathematically.

## Default eight-axis scorecard

Use these axes when the evidence is visible:

1. Preparation / unit turn.
2. Lower-body loading.
3. Hip-shoulder separation and release order.
4. Contact-height stability.
5. Contact spacing in front of the body.
6. Hitting-arm and racket structure.
7. Follow-through and deceleration.
8. Recovery and balance.

Use six axes when two are genuinely unobservable. Do not score a hidden axis as zero.

## Score anchors

Score in 0.5 increments and attach evidence plus confidence.

- 8.5–10: repeatable, phase-appropriate pattern with no clear limiting breakdown in the supplied evidence.
- 7.0–8.0: functional and mostly stable, with a smaller timing or consistency leak.
- 5.5–6.5: usable pattern, but a visible inefficiency or inconsistency limits the next phase.
- 4.0–5.0: clear limiting pattern that should be a training priority.
- 1.0–3.5: major technical breakdown repeated in usable footage.
- `N/A`: insufficient visibility or evidence.

A high score does not mean professional level. A single repetition caps confidence at low but does not automatically cap the numeric technique score.

Compute the overall as the weighted mean of known axes, rounded to one decimal. Default every weight to 1. Do not publish an overall score when fewer than six axes are known.

## NTRP-like estimate

Use NTRP only as a broad, non-official descriptive frame after checking the current official USTA guidance.

- One isolated stroke: technique-only band, low confidence.
- Five or more repetitions of forehand and backhand: broad baseline-stroke band, low to medium confidence.
- Serve, return, groundstrokes, volleys, movement, and point play: self-rating band, medium confidence.
- Official league or tournament results: report the official rating instead of inventing a visual estimate.

Prefer a range such as `2.5–3.0`. If an editorial shorthand such as `3.0−` is used, explain that the minus sign is not an official USTA category.

## UTR and WTN

Verify current official definitions before citing scales or rules.

- Do not estimate UTR from technique video. Use a published UTR or report that match results are required.
- Do not estimate ITF World Tennis Number from technique video. Use a published WTN or report that match results are required.
- Do not reverse-engineer proprietary rating algorithms from a few informal scores.

## Rating evidence checklist

Record available evidence for:

- serve and second serve;
- return;
- forehand and backhand consistency;
- direction and depth control;
- volley / overhead;
- movement and recovery;
- point construction under pressure;
- match scores and opponent ratings.

List missing categories next to the confidence label.

## Scorecard JSON

Use this shape with `scripts/tennis_motion.py scorecard`:

```json
{
  "title": "Forehand training score",
  "dimensions": [
    {"key": "preparation", "label": "引拍 / 转肩", "score": 6.5, "confidence": "medium", "evidence": "unit turn visible"},
    {"key": "loading", "label": "屈膝储能", "score": 5.5, "confidence": "medium", "evidence": "knee angle rises before contact"}
  ],
  "level_estimate": {
    "system": "NTRP-like",
    "range": [2.5, 3.0],
    "display": "3.0−",
    "confidence": "low",
    "scope": "single forehand only",
    "formal": false
  }
}
```
