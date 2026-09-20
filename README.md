# SteelHacks XIII (2026) — independent project scoreboard

An unofficial, reproducible scoring of the public GitHub repositories built at SteelHacks XIII
(University of Pittsburgh, 19–20 September 2026). Snapshot taken 2026-09-20 12:30 UTC, about
two and a half hours before the submission deadline.

- **Report:** `report/index.html` (open in a browser; all English, no build step).
- **Rubric:** 40 points objective (git history and file-tree metrics computed by `scripts/metrics.py`
  and `scripts/score_obj.py`), 60 points subjective (reviewer evidence per repo in
  `data/evidence_*.json`, calibrated by the lead judge in `data/calibration.json`), plus a separate
  0–10 Wow index and a predicted human-judge rank range for a 3-minute live demo.
- **Tracks:** `data/tracks.json` — reconstructed from organizer wording quoted in participants' repos,
  because steelhacks.org and the Devpost page were unreachable from the analysis sandbox.
- **Rebuild:** clone the repos in `data/repos.txt` into `repos/`, run `scripts/metrics.py`,
  `scripts/score_obj.py`, then `scripts/build_report.py`.

Submission materials (video, slides, Devpost fields, team info) were deliberately not scored.
Scores are an independent estimate, not official results.
