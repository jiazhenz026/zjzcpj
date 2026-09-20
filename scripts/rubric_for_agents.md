# SteelHacks XIII (2026) — repo evidence-gathering brief

You are gathering evidence about hackathon projects so a lead judge can score them. Read-only: do NOT run code, install packages, hit the network, or modify anything under the repos directory. Everything is cloned locally already.

## Event context
- SteelHacks XIII, University of Pittsburgh, in-person, Sept 19 (hacking start 11:00 EDT) to Sept 20, 2026 (submission 11:00 EDT). Judging is a live 3-minute in-person demo.
- Official tracks (reconstructed from steelhacks.org/tracks via participants' notes):
  1. Compound — the financial-hack track (payments, fraud, small-business cash flow). Requires synthetic/sandbox data; excludes real financial records.
  2. Xtract (LANXESS) — turn varied incoming reports/documents into meaningful signals with source traceability and a usable output. Public/synthetic sources allowed.
  3. Beyond the Chatbot (NVIDIA Nemotron) — Nemotron doing something other than chat, with a clearly explained role and evidence it works (eval, comparison, benchmark, or documented failure). Stacks with every other track. 3 winning teams.
  4. Out Loud! (ElevenLabs) — voice/audio-first products using ElevenLabs.
  5. Seed Round (Pear VC & Afore Capital) — a real problem, a working product (not a pitch deck), and a reason to believe people want it.
  6. No Wrapper — no language model anywhere in the finished project; "something hard in a way you can explain, and a working demo judges can try"; classical ML is fine.
  7. Cold Start — first-time hackers / beginner track (eligibility-based).
  8. Presage (MLH partner) — vital signs / movement / emotion / focus tracking; sub-themes: Accessibility & Security (vital-sign auth or accessibility) and Productivity (focus/stress tools).
  9. Solana (MLH) — build on the Solana network.
  10. MLH bonus tracks: Best Use of Gemini API, Tiger Data, Snowflake, DigitalOcean, .Tech domain, ElevenLabs.
  Also "General / no track" if nothing fits.
- Submission-material completeness (video, slides, Devpost, team info) is explicitly NOT scored. Only project quality.

## What to do for each repo
1. Read the README fully (and any design/plan docs at the top level, briefly). Note the project name, one-line pitch, problem, target user, claimed tracks, claimed team size, any live URL.
2. Skim the file tree (ignore node_modules/.git). Identify the entry points and the core loop (e.g., UI → API → model → result; game loop; hardware → radio → app).
3. Open the main source files (the ones that implement the core loop, roughly 5–12 files) and verify: is the core loop actually wired end to end? What is mocked, fixture-backed, hardcoded, stubbed, or TODO? Are there error/loading states? Does it depend on paid/unstable services that could fail on stage?
4. Judge UI/experience from code + assets: styling system, number of screens/components, animations, 3D, maps, audio, hardware, game engine, physical interaction. Would a judge be able to *touch* it during a demo?
5. Note integrity/hygiene signals you actually see: pre-hackathon or template code (starter kits, copied projects, "won HackUTD" reuse), committed secrets or .env, AI-agent scaffolding (CLAUDE.md, AGENTS.md, handoff docs) and whether the docs are far larger than the code.
6. Think like a judge with 3 minutes: what is the single moment that could make them say "wow"? Classify it: NEW-ARENA (a problem space judges never considered), UNEXPECTED-TWIST (a common category done in a way nobody expected), VISCERAL (fun to play, beautiful, physical, audible, live), or NONE.

## Score anchors (preliminary; the lead judge re-calibrates across all batches)
- S1 Idea novelty (0–12): 0–3 seen many times (todo/budget tracker/generic chatbot/flashcards); 4–6 common category with one distinctive twist; 7–9 uncommon problem or a genuinely new mechanism; 10–12 a category judges have likely never seen.
- S2 Need / problem validity (0–10): 0–2 no clear user or invented need; 3–5 plausible but generic; 6–8 specific user with real pain, evidence given; 9–10 urgent, specific, credible with data/quotes/domain insight.
- S3 Track fit (0–8): 0–2 no official track fits or sponsor tech is superficial; 3–5 partial fit to one track; 6–7 strong fit to a track's stated criteria; 8 nails a track's criteria and credibly stacks with another.
- S4 Completeness / working state (0–15): 0–3 README or skeleton only; 4–7 parts exist but the core loop is not wired or is mostly mocked; 8–11 core loop works end to end with rough edges or fixtures; 12–15 polished end to end, error handling, real data path, eval or tests.
- S5 Eye-catching / demo appeal (0–15): 0–3 CLI/notebook/no UI; 4–7 basic UI; 8–11 attractive UI or an interactive/physical element; 12–15 visually striking, interactive, hardware/audio/live element judges can try.
- Wow index (0–10, judge-with-3-minutes lens ONLY, ignore architecture and code size): 0–2 none; 3–4 mild interest; 5–6 one clear "huh, neat"; 7–8 one strong wow; 9–10 multiple wows / unforgettable.

## Output
Write a JSON array to the output path given in your task, one object per repo, with exactly these keys:
repo (owner/name), project_name, one_liner, problem, target_user, claimed_tracks (list), best_fit_tracks (list from the official names above, ordered), team_size_claimed (int or null), live_url (string or null), stack (list), core_loop (string), wired_end_to_end (true/false/partial), mocked_or_hardcoded (string), demo_risks (string), ui_experience (string), physical_or_sensory (string: hardware/audio/game/3D/AR/map/none), integrity_flags (string), ai_scaffolding_flags (string), novelty_notes (string), need_notes (string), wow_moment (string), wow_type (NEW-ARENA|UNEXPECTED-TWIST|VISCERAL|NONE), scores {S1,S2,S3,S4,S5,wow} (numbers), score_rationale (string, ≤80 words), judge_summary (string, ≤60 words, plain English, what a judge would remember).

Keep each string concise. In your final message, give ONLY the output path and one line per repo: "owner/name — project_name — S1/S2/S3/S4/S5 wow=N".
