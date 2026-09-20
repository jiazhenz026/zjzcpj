#!/usr/bin/env python3
import json, math, re, os
M=json.load(open('metrics.json'))
OVERRIDE_LOC={'JamesCasella_Fish-Fighter':int(open('unz_loc.txt').read().strip()) if os.path.exists('unz_loc.txt') else 300,'Schnooz_Fuego_Data_Pipeline':673}
def interp(x,anchors):
    # anchors: list of (x,y) increasing; log-x interpolation
    if x<=anchors[0][0]: return anchors[0][1]
    for (x0,y0),(x1,y1) in zip(anchors,anchors[1:]):
        if x<=x1:
            lx0,lx1,lx=math.log(x0+1),math.log(x1+1),math.log(x+1)
            return y0+(y1-y0)*(lx-lx0)/(lx1-lx0)
    return anchors[-1][1]
RUN_PAT=re.compile(r'(npm (install|run|start|i\b)|pnpm|yarn|bun (run|install|dev)|pip install|pip3 install|python3? |uvicorn|flask run|docker (compose|run|build)|cargo run|go run|gradle|mvn|\./gradlew|streamlit run|expo start|npx |make\b|\bgodot\b|arduino|platformio|open .* in unity|unity)',re.I)
out=[]
for r in M:
    d=r['dir']; loc=OVERRIDE_LOC.get(d,r['code_loc'])
    o1=round(interp(loc,[(0,0),(100,1.5),(300,3),(1000,5),(3000,7),(8000,8.5),(15000,10)]),1)
    a=interp(r['commits_during_hackathon'],[(0,0),(1,1),(5,3),(15,5),(30,7),(60,9),(100,10)])
    b=interp(r['active_hours_during'],[(0,0),(1,1),(5,3),(10,5),(15,7),(20,9),(24,10)])
    o2=round(0.5*a+0.5*b,1)
    n=r['n_authors']; o3={0:0,1:2,2:3,3:4}.get(n,4.5)
    if n>=2 and (r['top_author_share'] or 1)<=0.6: o3=min(5,o3+0.5)
    h=r['has']; readme=''
    for f in os.listdir(os.path.join('repos',d)):
        if f.lower().startswith('readme'):
            try: readme+=open(os.path.join('repos',d,f),errors='replace').read()
            except: pass
    run_instr = bool(RUN_PAT.search(readme)) and r['readme_words']>=60
    o4=0; o4+=2 if h['manifest'] or d in OVERRIDE_LOC else 0
    o4+=2 if run_instr else (1 if r['readme_words']>=150 else 0)
    o4+=1 if h['gitignore'] else 0
    hyg=2
    if r['vendored_files_committed']>0: hyg-=1
    if r['secrets_found'] or r['env_files_committed']: hyg-=1
    o4+=max(hyg,0)
    o4+=1 if h['tests'] else 0
    o4+=1 if h['ci'] else 0
    o4+=1 if h['env_example'] else 0
    o4=min(o4,10)
    ratio=(r['loc_added_during_hackathon'] or 0)/max(loc,1) if loc else 0
    if d in OVERRIDE_LOC: ratio=1.0
    o5=5 if ratio>=0.95 else 4 if ratio>=0.8 else 3 if ratio>=0.6 else 2 if ratio>=0.4 else 1 if ratio>=0.2 else 0
    if loc==0: o5=0
    tot=round(o1+o2+o3+o4+o5,1)
    out.append({'dir':d,'repo':r['repo'],'code_loc':loc,'commits_during':r['commits_during_hackathon'],'commits_pre':r['commits_pre_hackathon'],'active_hours':r['active_hours_during'],'n_authors':n,'top_share':r['top_author_share'],'readme_words':r['readme_words'],'run_instr':run_instr,'has':h,'vendored':r['vendored_files_committed'],'secrets':len(r['secrets_found'])+len(r['env_files_committed']),'fresh_ratio':round(ratio,2),'O1':o1,'O2':o2,'O3':o3,'O4':o4,'O5':o5,'OBJ':tot,'langs':r['loc_by_lang'],'first_commit':r['first_commit'],'last_commit':r['last_commit'],'ai_coauthored':r['ai_coauthored_commits']})
json.dump(out,open('obj_scores.json','w'),indent=1)
print(f"{'repo':<46}{'loc':>7}{'cmt':>5}{'hrs':>4}{'au':>3}{'fr':>5} | O1  O2  O3  O4  O5 | OBJ")
for o in sorted(out,key=lambda x:-x['OBJ']):
    print(f"{o['repo']:<46}{o['code_loc']:>7}{o['commits_during']:>5}{o['active_hours']:>4}{o['n_authors']:>3}{o['fresh_ratio']:>5} | {o['O1']:>3} {o['O2']:>3} {o['O3']:>3} {o['O4']:>3} {o['O5']:>3} | {o['OBJ']}")
