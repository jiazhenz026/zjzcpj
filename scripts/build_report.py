#!/usr/bin/env python3
"""Build the SteelHacks XIII scoreboard HTML from objective metrics, agent evidence and judge calibration."""
import json, glob, html, os, datetime, math

BASE = os.path.dirname(os.path.abspath(__file__))
def load(p, default=None):
    fp = os.path.join(BASE, p)
    if not os.path.exists(fp):
        return default
    return json.load(open(fp))

OBJ = {o['dir']: o for o in load('obj_scores.json')}
# real owner/name for every cloned dir (dir names use '_' for '/')
DIR2REPO = {}
try:
    for line in open(os.path.join(BASE, 'repos.txt')):
        line = line.strip()
        if line: DIR2REPO[line.replace('/', '_')] = line
except FileNotFoundError:
    pass
for d, o in OBJ.items():
    o['repo'] = DIR2REPO.get(d, o['repo'])
TRACKS = load('tracks.json')
TRACK_BY_KEY = {t['key']: t for t in TRACKS}
CAL = load('calibration.json', {})           # judge overrides keyed by dir
META = load('meta.json', {})
EXCLUDED_404 = META.get('not_accessible', [])

# ---- merge agent evidence -------------------------------------------------
EV = {}
for f in sorted(glob.glob(os.path.join(BASE, 'agent_*.json'))):
    for rec in json.load(open(f)):
        d = rec['repo'].replace('/', '_')
        EV[d] = rec

TRACK_NAME_TO_KEY = {}
for t in TRACKS:
    TRACK_NAME_TO_KEY[t['name'].lower()] = t['key']
ALIASES = {
    'nemotron': 'nemotron', 'beyond the chatbot': 'nemotron', 'nvidia': 'nemotron', 'beyond the chatbot (nvidia nemotron)': 'nemotron',
    'out loud': 'outloud', 'out loud!': 'outloud', 'elevenlabs': 'outloud', 'out loud! (elevenlabs)': 'outloud',
    'seed round': 'seed', 'seed round (pear vc & afore capital)': 'seed', 'pear': 'seed',
    'no wrapper': 'nowrapper', 'cold start': 'coldstart', 'presage': 'presage', 'solana': 'solana',
    'compound': 'compound', 'xtract': 'xtract', 'xtract (lanxess)': 'xtract', 'lanxess': 'xtract',
    'mlh': 'mlh', 'mlh bonus tracks': 'mlh', 'gemini': 'mlh', 'tiger data': 'mlh', 'digitalocean': 'mlh', '.tech': 'mlh', 'snowflake': 'mlh',
    'general': 'general', 'general / no track': 'general', 'general (no sponsor track)': 'general', 'none': 'general', 'no track': 'general',
}
def to_key(name):
    n = (name or '').strip().lower()
    if n in TRACK_BY_KEY: return n
    if n in TRACK_NAME_TO_KEY: return TRACK_NAME_TO_KEY[n]
    for a, k in ALIASES.items():
        if a in n: return k
    return None

# ---- assemble projects ----------------------------------------------------
S_MAX = {'S1': 12, 'S2': 10, 'S3': 8, 'S4': 15, 'S5': 15}
projects = []
placeholders = []
for d, o in OBJ.items():
    ev = EV.get(d)
    cal = CAL.get(d, {})
    if cal.get('exclude'):
        placeholders.append({'dir': d, 'repo': o['repo'], 'reason': cal.get('exclude'), 'obj': o})
        continue
    if ev is None:
        placeholders.append({'dir': d, 'repo': o['repo'], 'reason': cal.get('exclude') or 'Placeholder repository: README only or no readable source at snapshot time.', 'obj': o})
        continue
    sc = dict(ev.get('scores', {}))
    for k in list(S_MAX) + ['wow']:
        if k in cal: sc[k] = cal[k]
        sc[k] = float(sc.get(k, 0))
        if k != 'wow': sc[k] = max(0, min(S_MAX[k], sc[k]))
        else: sc[k] = max(0, min(10, sc[k]))
    subj = round(sum(sc[k] for k in S_MAX), 1)
    # tracks
    keys = []
    for name in (cal.get('tracks') or ev.get('best_fit_tracks') or []):
        k = to_key(name)
        if k and k not in keys: keys.append(k)
    if not keys: keys = ['general']
    obj_total = o['OBJ']
    # objective override (e.g., code shipped as zip)
    if 'OBJ' in cal: obj_total = cal['OBJ']
    projects.append({
        'dir': d, 'repo': ev.get('repo') or o['repo'], 'name': cal.get('name') or ev.get('project_name') or o['repo'].split('/')[-1],
        'one_liner': cal.get('one_liner') or ev.get('one_liner', ''),
        'ev': ev, 'obj': o, 'cal': cal, 'scores': sc, 'SUBJ': subj, 'OBJ': obj_total,
        'TOTAL': round(obj_total + subj, 1), 'tracks': keys,
        'judge_note': cal.get('judge_note') or ev.get('judge_summary', ''),
        'wow_type': cal.get('wow_type') or ev.get('wow_type', 'NONE'),
        'wow_moment': cal.get('wow_moment') or ev.get('wow_moment', ''),
    })

projects.sort(key=lambda p: (-p['TOTAL'], -p['scores']['wow'], p['name'].lower()))
for i, p in enumerate(projects, 1): p['rank'] = i

# ---- human-judge rank range (3-minute demo, wow-dominated) -----------------
def judge_score(p):
    s = p['scores']
    return 0.6 * (s['wow'] / 10) + 0.25 * (s['S5'] / 15) + 0.15 * (s['S1'] / 12)
by_track = {}
for p in projects:
    for k in p['tracks']:
        by_track.setdefault(k, []).append(p)
for k, lst in by_track.items():
    lst.sort(key=lambda p: (-p['TOTAL'], -p['scores']['wow']))
    for i, p in enumerate(lst, 1): p.setdefault('track_rank', {})[k] = i
    js = sorted(lst, key=lambda p: (-judge_score(p), -p['TOTAL']))
    n = len(js)
    for i, p in enumerate(js, 1):
        # spread widens with field size and with how close the judge scores are
        lo = max(1, i - (1 if n > 3 else 0))
        hi = min(n, i + (2 if n > 6 else 1 if n > 2 else 0))
        rng = p['cal'].get('judge_range', {}).get(k) if isinstance(p['cal'].get('judge_range'), dict) else None
        p.setdefault('judge_range', {})[k] = rng or (f"{lo}" if lo == hi else f"{lo}–{hi}")
        p.setdefault('judge_rank', {})[k] = i

# ---- helpers ----------------------------------------------------------------
def e(s): return html.escape(str(s if s is not None else ''))
def fmt(x):
    if isinstance(x, float) and x.is_integer(): return str(int(x))
    return str(x)
def track_label(k): return TRACK_BY_KEY.get(k, {'name': k})['name']
def repo_link(repo): return f'<a href="https://github.com/{e(repo)}" target="_blank" rel="noopener">{e(repo)}</a>'
def chips(keys): return ''.join(f'<span class="chip t-{e(k)}">{e(track_label(k))}</span>' for k in keys)

snapshot = META.get('snapshot_utc', datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))
n_found = len(OBJ) + len(EXCLUDED_404)
n_scored = len(projects)

# ---- chart (SVG) --------------------------------------------------------------
def chart_svg(ps):
    row_h, pad_l, pad_r, pad_t, w = 22, 236, 56, 28, 900
    h = pad_t + row_h * len(ps) + 34
    scale = (w - pad_l - pad_r) / 100
    out = [f'<svg class="lb-chart" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Stacked bars of objective and subjective score per project">']
    for t in (0, 20, 40, 60, 80, 100):
        x = pad_l + t * scale
        out.append(f'<line x1="{x:.1f}" y1="{pad_t-6}" x2="{x:.1f}" y2="{h-30}" class="grid"/>')
        out.append(f'<text x="{x:.1f}" y="{h-12}" class="tick" text-anchor="middle">{t}</text>')
    for i, p in enumerate(ps):
        y = pad_t + i * row_h
        bh = 14
        xo = p['OBJ'] * scale; xs = p['SUBJ'] * scale
        out.append(f'<g class="bar" data-idx="{i}" tabindex="0" data-name="{e(p["name"])}" data-obj="{fmt(p["OBJ"])}" data-subj="{fmt(p["SUBJ"])}" data-total="{fmt(p["TOTAL"])}" data-wow="{fmt(p["scores"]["wow"])}">')
        out.append(f'<rect x="0" y="{y}" width="{w}" height="{row_h}" class="hit"/>')
        out.append(f'<text x="{pad_l-10}" y="{y+bh/2+4}" class="ylab" text-anchor="end">{e(p["name"][:30])}</text>')
        out.append(f'<rect x="{pad_l}" y="{y}" width="{max(xo-2,0):.1f}" height="{bh}" class="seg obj"/>')
        out.append(f'<rect x="{pad_l+xo:.1f}" y="{y}" width="{max(xs-2,0):.1f}" height="{bh}" rx="4" class="seg subj"/>')
        out.append(f'<text x="{pad_l+xo+xs+6:.1f}" y="{y+bh/2+4}" class="val">{fmt(p["TOTAL"])}</text>')
        out.append('</g>')
    out.append('</svg>')
    return ''.join(out)

# ---- sections -------------------------------------------------------------------
def method_html():
    return f'''
<section id="method" class="sec">
<h2>Method and rubric</h2>
<p class="lede">Every scored repository was cloned locally at the snapshot time and analysed two ways. A script computed the <strong>objective score (40 points)</strong> from git history and the file tree. Reviewers read the README and core source of each project to produce the <strong>subjective score (60 points)</strong>, then the lead judge re-calibrated all scores on a single scale. A separate <strong>Wow index (0–10)</strong> models what a human judge sees in a 3-minute live demo. Submission materials (video, slides, Devpost fields, team info) are deliberately <em>not</em> scored: the deadline had not passed at snapshot time.</p>
<div class="cols">
<div>
<h3>Objective score · 40 pts · machine-computed</h3>
<table class="rub">
<thead><tr><th>Component</th><th>Pts</th><th>How it is computed</th></tr></thead>
<tbody>
<tr><td>O1 Code substance</td><td>10</td><td>Non-blank lines of source, excluding vendored directories, lockfiles, minified bundles, data/asset files and docs. Log-scaled: 100 → 1.5, 1k → 5, 3k → 7, 8k → 8.5, 15k+ → 10.</td></tr>
<tr><td>O2 Build effort</td><td>10</td><td>Half from commits inside the hacking window (Sat 11:00 EDT onward; 5 → 3, 30 → 7, 100+ → 10), half from distinct hours with commits (10 → 5, 24 → 10).</td></tr>
<tr><td>O3 Team collaboration</td><td>5</td><td>Distinct human commit authors (1 → 2, 2 → 3, 3 → 4, 4+ → 4.5) plus 0.5 when no author holds more than 60% of commits.</td></tr>
<tr><td>O4 Runnability &amp; hygiene</td><td>10</td><td>Build manifest 2 · README with run instructions 2 · .gitignore 1 · no vendored deps or secrets/.env committed 2 · tests 1 · CI/deploy config 1 · env example 1.</td></tr>
<tr><td>O5 Fresh-code integrity</td><td>5</td><td>Share of source added by commits inside the window versus total source (≥95% → 5, ≥80% → 4, ≥60% → 3, ≥40% → 2, ≥20% → 1).</td></tr>
</tbody></table>
</div>
<div>
<h3>Subjective score · 60 pts · reviewed, then calibrated</h3>
<table class="rub">
<thead><tr><th>Component</th><th>Pts</th><th>Anchors</th></tr></thead>
<tbody>
<tr><td>S1 Idea novelty</td><td>12</td><td>0–3 seen many times · 4–6 common category with one twist · 7–9 uncommon problem or new mechanism · 10–12 a category judges have never seen.</td></tr>
<tr><td>S2 Need / problem validity</td><td>10</td><td>0–2 no clear user · 3–5 plausible but generic · 6–8 specific user with real pain · 9–10 urgent and credible with evidence.</td></tr>
<tr><td>S3 Track fit</td><td>8</td><td>0–2 no track or superficial sponsor use · 3–5 partial fit · 6–7 strong fit to the track's stated criteria · 8 nails one track and credibly stacks another.</td></tr>
<tr><td>S4 Completeness</td><td>15</td><td>0–3 skeleton · 4–7 core loop not wired or mostly mocked · 8–11 works end to end with rough edges or fixtures · 12–15 polished, real data path, error handling, eval or tests.</td></tr>
<tr><td>S5 Demo appeal</td><td>15</td><td>0–3 CLI/notebook · 4–7 basic UI · 8–11 attractive UI or an interactive/physical element · 12–15 visually striking, something judges can touch, hear or play.</td></tr>
</tbody></table>
</div>
</div>
<h3>Wow index and the human-judge rank range</h3>
<p>A judge with three minutes never reads architecture, counts lines or weighs technical depth. The Wow index scores only what lands in those minutes: a <span class="wt NEW-ARENA">new arena</span> nobody expected, an <span class="wt UNEXPECTED-TWIST">unexpected twist</span> on something everyone builds, or something <span class="wt VISCERAL">visceral</span>: fun to play, beautiful, physical, audible. 0–2 nothing · 3–4 mild interest · 5–6 one clear "huh, neat" · 7–8 one strong wow · 9–10 several wows.</p>
<p>The <strong>human-judge rank range</strong> shown per track re-orders the field by a demo-day model (60% Wow, 25% demo appeal, 15% novelty) and widens it by one place above and one to two places below to reflect judge variance and demo luck. It is a prediction of where live judges would land, not the score-based rank.</p>
<h3>Coverage and limits</h3>
<ul>
<li>Discovery: GitHub repository search for "steelhacks", "steel hacks", "steelhacks xiii" and "steelhacks 2026" restricted to repositories pushed after 18 Sep 2026 (all result pages), the steelhacks and steelhacksxiii topics, and web search. Repositories that never mention SteelHacks are invisible to this method.</li>
<li>The organizer sites (steelhacks.org, the Devpost page) were unreachable from this sandbox; track definitions were reconstructed from organizer wording quoted inside participants' planning documents and from search snippets.</li>
<li>Scores reflect the repository state at {e(snapshot)}, roughly two and a half hours before the submission deadline. Teams were still pushing.</li>
<li>Nothing was executed. "Works end to end" means the code path is wired in source, not that it was run.</li>
</ul>
</section>'''

def tracks_html():
    cards = []
    for t in TRACKS:
        n = len(by_track.get(t['key'], []))
        cards.append(f'<div class="tcard"><div class="tcard-h"><span class="chip t-{e(t["key"])}">{e(t["name"])}</span><span class="muted">{e(t["sponsor"])}</span></div><p>{e(t["summary"])}</p><p class="muted small">Entrants in this analysis: {n} · Source: {e(t["evidence"])}</p></div>')
    return f'<section id="tracks" class="sec"><h2>Official tracks (reconstructed)</h2><p class="lede">SteelHacks XIII, University of Pittsburgh, 19–20 September 2026. Hacking opened Saturday 11:00 EDT; submissions close Sunday 11:00 EDT. Projects may enter several tracks; the Nemotron track stacks with every other track.</p><div class="tgrid">{"".join(cards)}</div></section>'

def summary_html():
    top = projects[:5]
    wow = sorted(projects, key=lambda p: (-p['scores']['wow'], -p['TOTAL']))[:5]
    picks = []
    for t in TRACKS:
        lst = by_track.get(t['key'], [])
        if not lst: continue
        best = lst[0]
        picks.append(f'<li><span class="chip t-{e(t["key"])}">{e(t["name"])}</span> <strong>{e(best["name"])}</strong> <span class="muted">({fmt(best["TOTAL"])} pts · wow {fmt(best["scores"]["wow"])}, {len(lst)} entrants)</span></li>')
    obs = META.get('observations', [])
    obs_html = ''.join(f'<li>{o}</li>' for o in obs)
    return f'''
<section id="summary" class="sec">
<h2>Summary</h2>
<div class="cols3">
<div><h3>Top 5 by total score</h3><ol class="rank">{"".join(f'<li><strong>{e(p["name"])}</strong> <span class="muted">{fmt(p["TOTAL"])} · {e(p["repo"])}</span></li>' for p in top)}</ol></div>
<div><h3>Top 5 by Wow index</h3><ol class="rank">{"".join(f'<li><strong>{e(p["name"])}</strong> <span class="muted">wow {fmt(p["scores"]["wow"])} · {e(p["wow_type"].replace("-"," ").title())}</span></li>' for p in wow)}</ol></div>
<div><h3>Score leader per track</h3><ul class="rank plain">{"".join(picks)}</ul></div>
</div>
<h3>What the field looks like</h3>
<ul class="obs">{obs_html}</ul>
</section>'''

def leaderboard_html():
    rows = []
    for p in projects:
        s = p['scores']; o = p['obj']
        prim = p['tracks'][0]
        jr = p['judge_range'].get(prim, '')
        rows.append(f'''<tr data-tracks="{e(' '.join(p['tracks']))}" data-name="{e(p['name'].lower())}">
<td class="num">{p['rank']}</td>
<td><a href="#d-{e(p['dir'])}" class="pname">{e(p['name'])}</a><div class="small muted">{repo_link(p['repo'])}</div></td>
<td class="chips">{chips(p['tracks'])}</td>
<td class="num">{fmt(o['O1'])}</td><td class="num">{fmt(o['O2'])}</td><td class="num">{fmt(o['O3'])}</td><td class="num">{fmt(o['O4'])}</td><td class="num">{fmt(o['O5'])}</td>
<td class="num strong obj-c">{fmt(p['OBJ'])}</td>
<td class="num">{fmt(s['S1'])}</td><td class="num">{fmt(s['S2'])}</td><td class="num">{fmt(s['S3'])}</td><td class="num">{fmt(s['S4'])}</td><td class="num">{fmt(s['S5'])}</td>
<td class="num strong subj-c">{fmt(p['SUBJ'])}</td>
<td class="num total">{fmt(p['TOTAL'])}</td>
<td class="num"><span class="wow w{int(round(s['wow']))}">{fmt(s['wow'])}</span></td>
<td class="num">{e(jr)}<div class="small muted">in {e(track_label(prim))}</div></td>
<td class="note">{e(p['judge_note'])}</td>
</tr>''')
    filters = ''.join(f'<button class="fbtn" data-f="{e(t["key"])}">{e(t["name"])} <span class="cnt">{len(by_track.get(t["key"], []))}</span></button>' for t in TRACKS if by_track.get(t['key']))
    return f'''
<section id="leaderboard" class="sec">
<h2>Overall leaderboard</h2>
<p class="lede">Objective (blue) and subjective (orange) stack to the total out of 100. Hover or focus a bar for the breakdown. Rank ties are broken by Wow index.</p>
<div class="legend"><span><i class="sw obj"></i>Objective · 40</span><span><i class="sw subj"></i>Subjective · 60</span></div>
<div class="chart-wrap">{chart_svg(projects)}<div class="tip" id="tip" hidden></div></div>
<div class="controls"><input id="q" type="search" placeholder="Filter by project name…" aria-label="Filter by project name"><div class="fbtns"><button class="fbtn on" data-f="all">All <span class="cnt">{len(projects)}</span></button>{filters}</div></div>
<div class="tbl-wrap"><table class="lb" id="lb">
<thead><tr>
<th data-k="0" class="num">#</th><th data-k="1">Project</th><th>Tracks</th>
<th data-k="3" class="num" title="Code substance">O1</th><th data-k="4" class="num" title="Build effort">O2</th><th data-k="5" class="num" title="Team">O3</th><th data-k="6" class="num" title="Runnability and hygiene">O4</th><th data-k="7" class="num" title="Fresh code">O5</th><th data-k="8" class="num obj-c">Obj/40</th>
<th data-k="9" class="num" title="Novelty">S1</th><th data-k="10" class="num" title="Need">S2</th><th data-k="11" class="num" title="Track fit">S3</th><th data-k="12" class="num" title="Completeness">S4</th><th data-k="13" class="num" title="Demo appeal">S5</th><th data-k="14" class="num subj-c">Subj/60</th>
<th data-k="15" class="num">Total</th><th data-k="16" class="num">Wow</th><th>Judge range</th><th>What a judge remembers</th>
</tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
</section>'''

def track_rank_html():
    secs = []
    for t in TRACKS:
        lst = by_track.get(t['key'], [])
        if not lst: continue
        rows = []
        for p in lst:
            k = t['key']
            rows.append(f'<tr><td class="num">{p["track_rank"][k]}</td><td><a href="#d-{e(p["dir"])}" class="pname">{e(p["name"])}</a><div class="small muted">{e(p["one_liner"])}</div></td><td class="num">{fmt(p["OBJ"])}</td><td class="num">{fmt(p["SUBJ"])}</td><td class="num total">{fmt(p["TOTAL"])}</td><td class="num"><span class="wow w{int(round(p["scores"]["wow"]))}">{fmt(p["scores"]["wow"])}</span></td><td class="num">{e(p["judge_range"][k])}</td><td class="note">{e(p["wow_moment"])}</td></tr>')
        secs.append(f'<div class="trank"><h3><span class="chip t-{e(t["key"])}">{e(t["name"])}</span> <span class="muted">{e(t["sponsor"])} · {len(lst)} entrants</span></h3><div class="tbl-wrap"><table class="lb small-t"><thead><tr><th class="num">#</th><th>Project</th><th class="num">Obj</th><th class="num">Subj</th><th class="num">Total</th><th class="num">Wow</th><th class="num">Judge range</th><th>Wow moment</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></div>')
    return f'<section id="track-rankings" class="sec"><h2>Rankings by track</h2><p class="lede">A project appears in every track it credibly fits. "Judge range" is the predicted placing from a 3-minute live demo, ordered by Wow first; "#" is the score-based rank.</p>{"".join(secs)}</section>'

def dossier_html():
    items = []
    for p in projects:
        ev = p['ev']; o = p['obj']; s = p['scores']; cal = p['cal']
        langs = ', '.join(f'{k} {v:,}' for k, v in list(o['langs'].items())[:4])
        flags = []
        if o['vendored']: flags.append('vendored dependencies committed')
        if o['secrets']: flags.append('secret-like strings or .env committed')
        if o['commits_pre'] and o['fresh_ratio'] < 0.8: flags.append(f"{o['commits_pre']} pre-window commits, {int(o['fresh_ratio']*100)}% of code fresh")
        hyg = '; '.join(flags) if flags else 'clean'
        def row(k, v):
            return f'<div class="kv"><dt>{k}</dt><dd>{e(v)}</dd></div>' if v else ''
        wired = ev.get('wired_end_to_end')
        wired_s = {True: 'yes', False: 'no', 'partial': 'partial'}.get(wired, str(wired))
        items.append(f'''
<details class="dossier" id="d-{e(p['dir'])}">
<summary><span class="num rk">#{p['rank']}</span><span class="dname">{e(p['name'])}</span><span class="muted dline">{e(p['one_liner'])}</span><span class="dscore">{fmt(p['TOTAL'])}<small>/100</small></span><span class="wow w{int(round(s['wow']))}">wow {fmt(s['wow'])}</span></summary>
<div class="dbody">
<div class="dmeta">{repo_link(p['repo'])} · {chips(p['tracks'])} · team size claimed: {e(ev.get('team_size_claimed') or '?')}{(' · live: <a href="'+e(ev['live_url'])+'" target="_blank" rel="noopener">'+e(ev['live_url'])+'</a>') if ev.get('live_url') else ''}</div>
<div class="cols">
<dl class="kvs">
{row('Problem', ev.get('problem'))}
{row('Target user', ev.get('target_user'))}
{row('Stack', ', '.join(ev.get('stack') or []))}
{row('Core loop', ev.get('core_loop'))}
{row('Wired end to end', wired_s)}
{row('Mocked / hardcoded', ev.get('mocked_or_hardcoded'))}
{row('Demo risks', ev.get('demo_risks'))}
{row('UI / experience', ev.get('ui_experience'))}
{row('Physical or sensory', ev.get('physical_or_sensory'))}
</dl>
<dl class="kvs">
{row('Novelty', ev.get('novelty_notes'))}
{row('Need', ev.get('need_notes'))}
{row('Wow moment', p['wow_moment'] + (' [' + p['wow_type'].replace('-', ' ').lower() + ']' if p['wow_type'] else ''))}
{row('Integrity flags', ev.get('integrity_flags'))}
{row('AI scaffolding', ev.get('ai_scaffolding_flags'))}
{row('Judge calibration note', cal.get('note'))}
</dl>
</div>
<div class="dgrid">
<div class="dbox"><h4>Objective · {fmt(p['OBJ'])}/40</h4><table class="mini"><tr><td>O1 code substance</td><td class="num">{fmt(o['O1'])}/10</td><td class="muted">{o['code_loc']:,} lines · {e(langs)}</td></tr><tr><td>O2 build effort</td><td class="num">{fmt(o['O2'])}/10</td><td class="muted">{o['commits_during']} commits in window · {o['active_hours']} active hours</td></tr><tr><td>O3 team</td><td class="num">{fmt(o['O3'])}/5</td><td class="muted">{o['n_authors']} author(s) · top share {fmt(o['top_share'])}</td></tr><tr><td>O4 runnability &amp; hygiene</td><td class="num">{fmt(o['O4'])}/10</td><td class="muted">manifest {'✓' if o['has']['manifest'] else '–'} · run steps {'✓' if o['run_instr'] else '–'} · tests {'✓' if o['has']['tests'] else '–'} · CI/deploy {'✓' if o['has']['ci'] else '–'} · hygiene {e(hyg)}</td></tr><tr><td>O5 fresh code</td><td class="num">{fmt(o['O5'])}/5</td><td class="muted">{int(min(o['fresh_ratio'],1)*100)}% of source added in window · first commit {e(str(o['first_commit'])[:16])}</td></tr></table></div>
<div class="dbox"><h4>Subjective · {fmt(p['SUBJ'])}/60</h4><table class="mini"><tr><td>S1 novelty</td><td class="num">{fmt(s['S1'])}/12</td></tr><tr><td>S2 need</td><td class="num">{fmt(s['S2'])}/10</td></tr><tr><td>S3 track fit</td><td class="num">{fmt(s['S3'])}/8</td></tr><tr><td>S4 completeness</td><td class="num">{fmt(s['S4'])}/15</td></tr><tr><td>S5 demo appeal</td><td class="num">{fmt(s['S5'])}/15</td></tr><tr><td>Wow index</td><td class="num">{fmt(s['wow'])}/10</td></tr></table><p class="small">{e(ev.get('score_rationale', ''))}</p></div>
</div>
</div>
</details>''')
    return f'<section id="dossiers" class="sec"><h2>Project dossiers</h2><p class="lede">Evidence behind every score. Expand a project for the core loop, what is mocked, demo risks and the full breakdown.</p>{"".join(items)}</section>'


def results_html():
    res = META.get('actual_results') or []
    if not res: return ''
    blocks = []
    for r in res:
        k = r['track']; lst = by_track.get(k, [])
        rows = []
        for w in r['winners']:
            p = next((x for x in lst if x['name'].lower() == w.lower()), None)
            if p:
                rows.append(f'<tr><td><strong>{e(w)}</strong></td><td class="num">{p["track_rank"][k]} of {len(lst)}</td><td class="num">{e(p["judge_range"][k])}</td><td class="num">{fmt(p["TOTAL"])}</td><td class="num"><span class="wow w{int(round(p["scores"]["wow"]))}">{fmt(p["scores"]["wow"])}</span></td><td class="note">Predicted judge range {e(p["judge_range"][k])} in a field of {len(lst)}; the score-based rank was {p["track_rank"][k]}.</td></tr>')
            else:
                rows.append(f'<tr><td><strong>{e(w)}</strong></td><td class="num">—</td><td class="num">—</td><td class="num">—</td><td class="num">—</td><td class="note">Not in this analysis.</td></tr>')
        blocks.append(f'<h3><span class="chip t-{e(k)}">{e(track_label(k))}</span> <span class="muted">announced {e(r["announced"])}</span></h3><div class="tbl-wrap"><table class="lb small-t"><thead><tr><th>Winner</th><th class="num">Score rank</th><th class="num">Predicted judge range</th><th class="num">Total</th><th class="num">Wow</th><th>Read</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><p class="small muted">{e(r.get("note",""))}</p>')
    return f'''<section id="results" class="sec"><h2>Actual results vs prediction</h2><p class="lede">Official winners as they were announced, next to what this scoreboard predicted. Added after the ceremony; scores above were not changed.</p>{"".join(blocks)}
<p><strong>What the outcome says about the model.</strong> The Nemotron track was called correctly as Heard!'s best chance because it is the one track that explicitly asks for evidence, and Heard! shipped a written Nemotron eval. The predicted judge range (5–8) still undershot a win, which points to two adjustments for next time: the Wow model overweights visual spectacle relative to a moment the judge can trigger and hear personally, and objective penalties such as fresh-code integrity have no weight with live judges who never open git history.</p></section>'''

def appendix_html():
    rows = ''.join(f'<tr><td>{repo_link(x["repo"])}</td><td class="num">{x["obj"]["code_loc"]}</td><td class="num">{x["obj"]["commits_during"] + x["obj"]["commits_pre"]}</td><td>{e(x["reason"])}</td></tr>' for x in sorted(placeholders, key=lambda x: x['repo'].lower()))
    na = ''.join(f'<tr><td>{repo_link(x["repo"])}</td><td>{e(x["note"])}</td></tr>' for x in EXCLUDED_404)
    return f'''
<section id="appendix" class="sec">
<h2>Appendix</h2>
<h3>Repositories found but not scored</h3>
<div class="tbl-wrap"><table class="lb small-t"><thead><tr><th>Repository</th><th class="num">Source lines</th><th class="num">Commits</th><th>Reason</th></tr></thead><tbody>{rows}</tbody></table></div>
<h3>Indexed by search but no longer public at snapshot time</h3>
<div class="tbl-wrap"><table class="lb small-t"><thead><tr><th>Repository</th><th>What search snippets said</th></tr></thead><tbody>{na}</tbody></table></div>
<h3>Reproducibility</h3>
<p class="small">Pipeline: clone → <code>metrics.py</code> (git and file-tree metrics) → <code>score_obj.py</code> (objective rubric) → reviewer evidence JSON per repo → <code>calibration.json</code> (lead-judge adjustments, all logged in the dossiers) → <code>build_report.py</code>. Deterministic given the same snapshot.</p>
<p class="small muted">Prepared {e(snapshot)}. Not affiliated with SteelHacks, the University of Pittsburgh, or any sponsor. Scores are an independent estimate for planning, not official results.</p>
</section>'''

CSS = r'''
<style>
:root{
  --bg:#EEF0F3; --bg2:#F7F8FA; --ink:#171B21; --ink2:#4B5563; --muted:#6B7280; --line:#D5D9E0; --line2:#E5E8ED;
  --accent:#D9731A; --accent-ink:#8A4409; --steel:#2F4A6D;
  --obj:#2a78d6; --subj:#eb6834; --surface:#fcfcfb; --grid:#e6e6e3;
  --good:#1a7f37; --warn:#b45309; --bad:#b91c1c;
  --chip:#E3E7EE; --chip-ink:#2B3A4E;
  --w0:#E5E7EB; --w1:#E5E7EB; --w2:#DDE6F5; --w3:#C9DBF3; --w4:#B7D3F6; --w5:#9EC5F4; --w6:#86B6EF; --w7:#6DA7EC; --w8:#5598E7; --w9:#3987E5; --w10:#2A78D6;
  --wink-hi:#0B1F3A; --wink-lo:#ffffff;
  --font-d:"Barlow Condensed","Arial Narrow",Impact,sans-serif; --font-b:"IBM Plex Sans","Segoe UI",Helvetica,Arial,sans-serif; --font-m:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#12161B; --bg2:#1A1F26; --ink:#E6E8EB; --ink2:#B4BAC4; --muted:#8B93A1; --line:#2E3540; --line2:#252B34;
  --accent:#F0883E; --accent-ink:#F7B27A; --steel:#9DB6D6;
  --obj:#3987e5; --subj:#d95926; --surface:#1a1a19; --grid:#2e2e2c;
  --good:#3fb950; --warn:#e3a008; --bad:#f85149;
  --chip:#26303D; --chip-ink:#C9D4E3;
  --w0:#252B34; --w1:#252B34; --w2:#1E3252; --w3:#1C3C66; --w4:#184F95; --w5:#1C5CAB; --w6:#256ABF; --w7:#2A78D6; --w8:#3987E5; --w9:#5598E7; --w10:#6DA7EC;
  --wink-hi:#ffffff; --wink-lo:#0B1F3A;
}}
:root[data-theme="dark"]{
  --bg:#12161B; --bg2:#1A1F26; --ink:#E6E8EB; --ink2:#B4BAC4; --muted:#8B93A1; --line:#2E3540; --line2:#252B34;
  --accent:#F0883E; --accent-ink:#F7B27A; --steel:#9DB6D6;
  --obj:#3987e5; --subj:#d95926; --surface:#1a1a19; --grid:#2e2e2c;
  --good:#3fb950; --warn:#e3a008; --bad:#f85149;
  --chip:#26303D; --chip-ink:#C9D4E3;
  --w0:#252B34; --w1:#252B34; --w2:#1E3252; --w3:#1C3C66; --w4:#184F95; --w5:#1C5CAB; --w6:#256ABF; --w7:#2A78D6; --w8:#3987E5; --w9:#5598E7; --w10:#6DA7EC;
  --wink-hi:#ffffff; --wink-lo:#0B1F3A;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--font-b);font-size:15px;line-height:1.5;margin:0;padding-block:0 48px;padding-inline:clamp(16px,3vw,40px)}
a{color:var(--steel);text-decoration:none;border-bottom:1px solid transparent}a:hover{border-bottom-color:currentColor}
h1,h2,h3,h4{font-family:var(--font-d);font-weight:700;letter-spacing:.01em;text-wrap:balance;margin:0}
h1{font-size:clamp(40px,7vw,72px);line-height:.95;text-transform:uppercase}
h2{font-size:clamp(28px,4vw,40px);line-height:1;margin-bottom:10px;padding-top:10px;border-top:3px solid var(--ink)}
h3{font-size:22px;margin:22px 0 8px}
h4{font-size:18px;margin:0 0 6px}
.eyebrow{font-family:var(--font-m);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent-ink)}
header.top{max-width:1240px;margin:0 auto;padding-block:28px 18px}
.hero{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end}
.hero p.sub{font-size:17px;color:var(--ink2);max-width:62ch;margin:10px 0 0}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:22px}
.tile{background:var(--bg2);border:1px solid var(--line);padding:12px 14px}
.tile b{display:block;font-family:var(--font-d);font-size:36px;line-height:1;font-variant-numeric:tabular-nums}
.tile span{font-size:12.5px;color:var(--muted)}
nav.sticky{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);border-bottom:1px solid var(--line);margin-inline:calc(-1*clamp(16px,3vw,40px));padding-inline:clamp(16px,3vw,40px)}
nav.sticky ul{list-style:none;margin:0 auto;padding:0;display:flex;gap:4px 18px;flex-wrap:wrap;max-width:1240px;font-family:var(--font-d);font-size:17px;text-transform:uppercase;letter-spacing:.04em}
nav.sticky a{display:inline-block;padding:10px 0;color:var(--ink)}
main{max-width:1240px;margin:0 auto}
.sec{margin-top:44px}
.lede{font-size:16.5px;color:var(--ink2);max-width:80ch;margin:0 0 14px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:22px}
.cols3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:22px}
table{border-collapse:collapse;width:100%}
th,td{text-align:left;vertical-align:top;padding:7px 8px;border-bottom:1px solid var(--line2);font-size:13.5px}
th{font-family:var(--font-d);font-size:15px;letter-spacing:.03em;text-transform:uppercase;color:var(--ink2);background:var(--bg2);position:sticky;top:0}
td.num,th.num{text-align:right;font-family:var(--font-m);font-variant-numeric:tabular-nums;white-space:nowrap}
.rub td:nth-child(2){font-family:var(--font-m);text-align:right}
.tbl-wrap{overflow-x:auto;border:1px solid var(--line);background:var(--bg2)}
.lb th[data-k]{cursor:pointer;user-select:none}.lb th[data-k]:hover{color:var(--accent-ink)}
.lb th.sorted::after{content:" ▾";color:var(--accent)}.lb th.sorted.asc::after{content:" ▴"}
.lb td.total{font-weight:700;font-size:15px}
.obj-c{color:var(--obj)}.subj-c{color:var(--subj)}
.strong{font-weight:600}
.note{min-width:260px;max-width:420px;color:var(--ink2);font-size:13px}
.pname{font-weight:600;color:var(--ink)}
.small{font-size:12.5px}.muted{color:var(--muted)}
.chip{display:inline-block;font-family:var(--font-m);font-size:11px;letter-spacing:.02em;padding:2px 7px;background:var(--chip);color:var(--chip-ink);border-radius:3px;margin:1px 3px 1px 0;white-space:nowrap}
.chip.t-nemotron{background:#DCE9D5;color:#1F4D12}.chip.t-outloud{background:#F3E1DD;color:#7A2A1C}.chip.t-seed{background:#EADFF1;color:#4B2A6A}.chip.t-compound{background:#DCE6F3;color:#1F3A66}.chip.t-xtract{background:#E6E1D4;color:#4E3F17}.chip.t-nowrapper{background:#E2E2E2;color:#333}.chip.t-presage{background:#D9EDEA;color:#134E48}.chip.t-solana{background:#DDEBE8;color:#0F4A3F}.chip.t-general{background:var(--chip);color:var(--chip-ink)}.chip.t-mlh{background:#EFE6D2;color:#5B4310}.chip.t-coldstart{background:#DDEAF6;color:#1D4C7A}
:root[data-theme="dark"] .chip,:root:not([data-theme="light"]) .chip{filter:none}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) .chip[class*=" t-"]{background:#26303D;color:#C9D4E3}}
:root[data-theme="dark"] .chip[class*=" t-"]{background:#26303D;color:#C9D4E3}
.wow{display:inline-block;min-width:34px;text-align:center;font-family:var(--font-m);font-weight:600;padding:2px 6px;border-radius:3px;background:var(--w0);color:var(--ink)}
.wow.w6,.wow.w7,.wow.w8,.wow.w9,.wow.w10{color:var(--wink-hi)}
.wow.w0{background:var(--w0)}.wow.w1{background:var(--w1)}.wow.w2{background:var(--w2)}.wow.w3{background:var(--w3)}.wow.w4{background:var(--w4)}.wow.w5{background:var(--w5)}.wow.w6{background:var(--w6)}.wow.w7{background:var(--w7)}.wow.w8{background:var(--w8)}.wow.w9{background:var(--w9)}.wow.w10{background:var(--w10)}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) .wow.w4,:root:not([data-theme="light"]) .wow.w5{color:#fff}}
:root[data-theme="dark"] .wow.w4,:root[data-theme="dark"] .wow.w5{color:#fff}
.wt{font-family:var(--font-m);font-size:12px;padding:1px 6px;border-radius:3px;background:var(--chip);color:var(--chip-ink)}
.rank{padding-left:22px;margin:0}.rank li{margin:4px 0}.rank.plain{list-style:none;padding-left:0}
.obs li{margin:6px 0;max-width:90ch}
.tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.tcard{background:var(--bg2);border:1px solid var(--line);padding:12px 14px}.tcard p{margin:8px 0 0;font-size:13.5px}
.tcard-h{display:flex;justify-content:space-between;gap:8px;align-items:baseline;flex-wrap:wrap}
.legend{display:flex;gap:18px;font-size:13px;color:var(--ink2);margin:4px 0 6px}.sw{display:inline-block;width:14px;height:10px;margin-right:6px;vertical-align:-1px}.sw.obj{background:var(--obj)}.sw.subj{background:var(--subj);border-radius:0 3px 3px 0}
.chart-wrap{position:relative;overflow-x:auto;background:var(--surface);border:1px solid var(--line);padding:6px 4px}
.lb-chart{display:block;max-width:100%;height:auto;font-family:var(--font-b)}
.lb-chart .grid{stroke:var(--grid);stroke-width:1}
.lb-chart .tick{fill:var(--muted);font-size:11px;font-family:var(--font-m)}
.lb-chart .ylab{fill:var(--ink);font-size:12px}
.lb-chart .val{fill:var(--ink2);font-size:11px;font-family:var(--font-m)}
.lb-chart .seg.obj{fill:var(--obj)}.lb-chart .seg.subj{fill:var(--subj)}
.lb-chart .hit{fill:transparent}
.lb-chart .bar:hover .seg,.lb-chart .bar:focus .seg{filter:brightness(1.12)}
.lb-chart .bar:focus{outline:none}.lb-chart .bar:focus .hit{fill:color-mix(in srgb,var(--ink) 6%,transparent)}
.tip{position:absolute;pointer-events:none;background:var(--bg2);border:1px solid var(--line);padding:8px 10px;font-size:12.5px;line-height:1.35;box-shadow:0 4px 14px rgba(0,0,0,.12);min-width:180px}
.tip b{font-size:14px}.tip .r{display:flex;justify-content:space-between;gap:12px}.tip .r i{display:inline-block;width:10px;height:3px;margin-right:6px;vertical-align:middle}
.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:16px 0 8px}
#q{font:inherit;padding:7px 10px;border:1px solid var(--line);background:var(--bg2);color:var(--ink);min-width:220px}
.fbtns{display:flex;gap:6px;flex-wrap:wrap}
.fbtn{font:inherit;font-size:12.5px;padding:5px 9px;border:1px solid var(--line);background:var(--bg2);color:var(--ink);cursor:pointer;border-radius:3px}
.fbtn.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.fbtn .cnt{font-family:var(--font-m);opacity:.7;margin-left:4px}
.trank{margin-top:18px}
.dossier{border:1px solid var(--line);background:var(--bg2);margin-top:8px}
.dossier summary{display:grid;grid-template-columns:52px 1fr auto auto;gap:6px 12px;align-items:center;padding:10px 14px;cursor:pointer;list-style:none}
.dossier summary::-webkit-details-marker{display:none}
.dossier summary .rk{font-family:var(--font-m);color:var(--muted)}
.dossier summary .dname{font-family:var(--font-d);font-size:22px;line-height:1}
.dossier summary .dline{grid-column:2;font-size:13px}
.dossier summary .dscore{font-family:var(--font-d);font-size:26px;line-height:1;font-variant-numeric:tabular-nums;grid-row:1/3;grid-column:3;align-self:center}.dossier summary .dscore small{font-size:13px;color:var(--muted);margin-left:2px}
.dossier summary .wow{grid-row:1/3;grid-column:4;align-self:center}
.dossier[open] summary{border-bottom:1px solid var(--line)}
.dbody{padding:12px 14px 16px}
.dmeta{font-size:13px;margin-bottom:10px}
.kvs{margin:0}.kv{display:grid;grid-template-columns:130px 1fr;gap:8px;padding:4px 0;border-bottom:1px dotted var(--line2)}.kv dt{color:var(--muted);font-size:12.5px;padding-top:1px}.kv dd{margin:0;font-size:13.5px}
.dgrid{display:grid;grid-template-columns:1.4fr 1fr;gap:14px;margin-top:14px}
.dbox{border:1px solid var(--line2);padding:10px 12px;background:var(--bg)}
.mini td{padding:4px 6px;font-size:13px}
code{font-family:var(--font-m);font-size:12.5px;background:var(--chip);padding:1px 5px;border-radius:3px}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:900px){.cols,.cols3,.dgrid{grid-template-columns:1fr}.tiles{grid-template-columns:repeat(2,1fr)}.hero{grid-template-columns:1fr}.dossier summary{grid-template-columns:44px 1fr auto}.dossier summary .wow{grid-column:3;grid-row:2}.dossier summary .dscore{grid-column:3;grid-row:1}}
@media (prefers-reduced-motion: reduce){*{transition:none!important}}
</style>'''

JS = r'''
<script>
(function(){
  // chart tooltip
  var tip=document.getElementById('tip'), wrap=document.querySelector('.chart-wrap');
  function show(g,ev){
    if(!tip) return;
    tip.innerHTML='<b>'+g.dataset.name+'</b><div class="r"><span><i style="background:var(--obj)"></i>Objective</span><span>'+g.dataset.obj+' / 40</span></div><div class="r"><span><i style="background:var(--subj)"></i>Subjective</span><span>'+g.dataset.subj+' / 60</span></div><div class="r"><span>Total</span><strong>'+g.dataset.total+'</strong></div><div class="r"><span>Wow index</span><span>'+g.dataset.wow+' / 10</span></div>';
    tip.hidden=false;
    var r=wrap.getBoundingClientRect(); var x=(ev&&ev.clientX?ev.clientX-r.left:200)+14, y=(ev&&ev.clientY?ev.clientY-r.top:20)+wrap.scrollTop-10;
    if(x+220>wrap.clientWidth) x=Math.max(8,x-240);
    tip.style.left=x+'px'; tip.style.top=y+'px';
  }
  document.querySelectorAll('.lb-chart .bar').forEach(function(g){
    g.addEventListener('pointermove',function(ev){show(g,ev)});
    g.addEventListener('pointerleave',function(){tip.hidden=true});
    g.addEventListener('focus',function(){var b=g.getBoundingClientRect(),w=wrap.getBoundingClientRect();show(g,{clientX:b.left+240,clientY:b.top+8})});
    g.addEventListener('blur',function(){tip.hidden=true});
  });
  // filters
  var rows=[].slice.call(document.querySelectorAll('#lb tbody tr'));
  var cur='all', q='';
  function apply(){
    rows.forEach(function(tr){
      var okT=(cur==='all')||(' '+tr.dataset.tracks+' ').indexOf(' '+cur+' ')>=0;
      var okQ=!q||tr.dataset.name.indexOf(q)>=0;
      tr.hidden=!(okT&&okQ);
    });
  }
  document.querySelectorAll('.fbtn').forEach(function(b){b.addEventListener('click',function(){document.querySelectorAll('.fbtn').forEach(function(x){x.classList.remove('on')});b.classList.add('on');cur=b.dataset.f;apply();})});
  var qi=document.getElementById('q'); if(qi){qi.addEventListener('input',function(){q=qi.value.trim().toLowerCase();apply();})}
  // sorting
  var tbody=document.querySelector('#lb tbody');
  document.querySelectorAll('#lb th[data-k]').forEach(function(th){
    th.addEventListener('click',function(){
      var k=+th.dataset.k, asc=th.classList.contains('sorted')&&!th.classList.contains('asc');
      document.querySelectorAll('#lb th').forEach(function(x){x.classList.remove('sorted','asc')});
      th.classList.add('sorted'); if(asc) th.classList.add('asc');
      var num=th.classList.contains('num');
      rows.sort(function(a,b){
        var A=a.children[k].textContent.trim(), B=b.children[k].textContent.trim();
        if(num){A=parseFloat(A)||0;B=parseFloat(B)||0;return asc?A-B:B-A}
        return asc?A.localeCompare(B):B.localeCompare(A);
      });
      rows.forEach(function(r){tbody.appendChild(r)});
    });
  });
  // open dossier from hash
  function openHash(){var h=location.hash; if(h&&h.indexOf('#d-')===0){var d=document.querySelector(h); if(d){d.open=true}}}
  window.addEventListener('hashchange',openHash); openHash();
})();
</script>'''

def build():
    head = f'''<title>SteelHacks XIII Scoreboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
{CSS}
<header class="top">
<div class="eyebrow">Independent project scoreboard · University of Pittsburgh · 19–20 Sep 2026</div>
<div class="hero"><div><h1>SteelHacks XIII<br>Scoreboard</h1><p class="sub">{n_scored} public repositories from this year's hackathon, scored 100 points each: 40 machine-computed from the code and git history, 60 from a reviewed reading of what each project actually does, plus a separate Wow index for the 3-minute live demo. Snapshot {e(snapshot)}, before the submission deadline.</p></div></div>
<div class="tiles"><div class="tile"><b>{n_found}</b><span>repositories found</span></div><div class="tile"><b>{n_scored}</b><span>projects scored</span></div><div class="tile"><b>{len(placeholders) + len(EXCLUDED_404)}</b><span>placeholders or unreachable</span></div><div class="tile"><b>{len([t for t in TRACKS if by_track.get(t['key'])])}</b><span>tracks with entrants</span></div></div>
</header>
<nav class="sticky"><ul><li><a href="#summary">Summary</a></li><li><a href="#results">Results</a></li><li><a href="#method">Method</a></li><li><a href="#tracks">Tracks</a></li><li><a href="#leaderboard">Leaderboard</a></li><li><a href="#track-rankings">By track</a></li><li><a href="#dossiers">Dossiers</a></li><li><a href="#appendix">Appendix</a></li></ul></nav>
<main>'''
    body = summary_html() + results_html() + method_html() + tracks_html() + leaderboard_html() + track_rank_html() + dossier_html() + appendix_html()
    page = head + body + '</main>' + JS
    out = os.path.join(BASE, 'report.html')
    open(out, 'w').write(page)
    print('wrote', out, len(page), 'bytes;', n_scored, 'scored,', len(placeholders), 'placeholders')
    # also dump merged data
    json.dump([{k: v for k, v in p.items() if k not in ('ev', 'obj', 'cal')} | {'evidence': p['ev'], 'objective': p['obj']} for p in projects], open(os.path.join(BASE, 'final_scores.json'), 'w'), indent=1, default=str)

if __name__ == '__main__':
    build()
