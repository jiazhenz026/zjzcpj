#!/usr/bin/env python3
import os, sys, json, subprocess, re, datetime, collections
ROOT='/tmp/claude-0/-home-user-zjzcpj/56dabd89-f253-58f3-bb91-f7e189b0a41c/scratchpad/repos'
HACK_START=datetime.datetime(2026,9,19,15,0,tzinfo=datetime.timezone.utc)  # Sat 11:00 ET
VENDOR_DIRS={'node_modules','dist','build','.venv','venv','env','vendor','__pycache__','.next','.expo','target','out','.git','coverage','.turbo','.cache','Pods','DerivedData','.godot','.import','site-packages','.dart_tool','bin','obj','Library','Temp','.idea','.vscode','static/vendor','public/vendor','.agents','.claude','.cursor','.expo-shared'}
CODE_EXT={'.py':'Python','.js':'JavaScript','.jsx':'JavaScript','.ts':'TypeScript','.tsx':'TypeScript','.java':'Java','.kt':'Kotlin','.swift':'Swift','.c':'C','.h':'C','.cpp':'C++','.cc':'C++','.hpp':'C++','.cs':'C#','.go':'Go','.rs':'Rust','.rb':'Ruby','.php':'PHP','.dart':'Dart','.gd':'GDScript','.lua':'Lua','.html':'HTML','.css':'CSS','.scss':'CSS','.vue':'Vue','.svelte':'Svelte','.sql':'SQL','.sh':'Shell','.ino':'Arduino','.m':'ObjC','.r':'R','.jl':'Julia','.ex':'Elixir','.exs':'Elixir','.zig':'Zig','.asm':'Assembly','.s':'Assembly','.glsl':'GLSL','.wgsl':'WGSL','.tf':'Terraform','.yaml':'YAML','.yml':'YAML','.toml':'TOML','.json':'JSON','.md':'Markdown','.ipynb':'Notebook','.prisma':'Prisma','.sol':'Solidity','.hs':'Haskell','.ml':'OCaml','.nim':'Nim','.cshtml':'C#','.razor':'C#','.gdshader':'GDScript','.tscn':'Godot','.tres':'Godot','.unity':'Unity','.prefab':'Unity','.mjs':'JavaScript','.cjs':'JavaScript','.mts':'TypeScript','.pyw':'Python'}
NONCODE={'YAML','TOML','JSON','Markdown','Godot','Unity','Notebook'}
GEN_PAT=re.compile(r'(\.min\.(js|css)$|lock(\.json|\.yaml|file)?$|package-lock\.json$|yarn\.lock$|pnpm-lock\.yaml$|bun\.lock$|poetry\.lock$|uv\.lock$|Cargo\.lock$|\.map$|\.snap$)')
SECRET_PAT=re.compile(r'(sk-[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|ghp_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,}|nvapi-[A-Za-z0-9_-]{20,}|eyJhbGciOi[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{30,}|sk_live_[A-Za-z0-9]{20,}|sk_test_[A-Za-z0-9]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY)')
def sh(cmd,cwd):
    return subprocess.run(cmd,cwd=cwd,shell=True,capture_output=True,text=True,errors='replace').stdout
def analyze(d):
    p=os.path.join(ROOT,d); r={'dir':d,'repo':d.replace('__','/')}
    # git
    log=sh("git log --all --format='%H|%aI|%an|%ae|%s' --no-merges",p).strip().splitlines()
    merges=sh("git log --all --format='%H' --merges",p).strip().splitlines()
    commits=[]
    for l in log:
        h,dt,an,ae,msg=l.split('|',4)
        commits.append({'h':h,'t':datetime.datetime.fromisoformat(dt),'an':an,'ae':ae,'msg':msg})
    r['commits_total']=len(commits); r['merge_commits']=len([m for m in merges if m])
    r['first_commit']=min(c['t'] for c in commits).isoformat() if commits else None
    r['last_commit']=max(c['t'] for c in commits).isoformat() if commits else None
    pre=[c for c in commits if c['t']<HACK_START]; dur=[c for c in commits if c['t']>=HACK_START]
    r['commits_pre_hackathon']=len(pre); r['commits_during_hackathon']=len(dur)
    authors=collections.Counter()
    for c in commits:
        key=c['an'].strip().lower()
        if 'github-actions' in c['ae'] or 'noreply@github.com' in c['ae'] and c['an'].lower() in ('github','github actions'): continue
        authors[key]+=1
    bots={a for a in authors if 'bot' in a or 'copilot' in a or 'claude' in a or 'codex' in a or 'dependabot' in a}
    r['authors']=dict(authors); r['n_authors']=len([a for a in authors if a not in bots]); r['bot_authors']=list(bots)
    # commit distribution: share of top author
    if authors:
        top=max(authors.values()); r['top_author_share']=round(top/sum(authors.values()),2)
    else: r['top_author_share']=None
    msgs=[c['msg'] for c in commits]
    r['avg_msg_len']=round(sum(len(m) for m in msgs)/len(msgs),1) if msgs else 0
    lowq=[m for m in msgs if len(m.strip())<8 or re.fullmatch(r'(update|fix|test|wip|asdf|stuff|changes|commit|push|save|.|\.+|updates?|fixes?)( ?\d*)?',m.strip().lower())]
    r['low_quality_msg_share']=round(len(lowq)/len(msgs),2) if msgs else None
    # hours active during hackathon
    hrs=set((c['t'].astimezone(datetime.timezone.utc)).strftime('%Y-%m-%dT%H') for c in dur)
    r['active_hours_during']=len(hrs)
    # AI tooling signals in git
    ai_co=len([c for c in commits if re.search(r'co-authored-by:.*(claude|copilot|codex|cursor|gpt|gemini)',sh(f"git log -1 --format=%B {c['h']}",p),re.I)])
    r['ai_coauthored_commits']=ai_co
    # files
    loc=collections.Counter(); files=collections.Counter(); total_files=0; big=[]; secrets=[]; env_files=[]; vendored_files=0; vendored_dirs=set()
    has={'readme':False,'tests':False,'ci':False,'docker':False,'manifest':False,'env_example':False,'gitignore':False,'license':False,'lint':False,'ts':False,'assets':0,'notebooks':0}
    readme_text=''; manifests=[]
    for root,dirs,fs in os.walk(p):
        rel=os.path.relpath(root,p)
        parts=rel.split(os.sep) if rel!='.' else []
        if any(x in VENDOR_DIRS for x in parts):
            vendored_files+=len(fs); vendored_dirs.add(parts[0] if parts else '')
            dirs[:]=[]; continue
        dirs[:]=[x for x in dirs if x not in VENDOR_DIRS]
        for f in fs:
            fp=os.path.join(root,f); total_files+=1
            rp=os.path.join(rel,f) if rel!='.' else f
            try: sz=os.path.getsize(fp)
            except: continue
            if sz>5_000_000: big.append((rp,sz))
            low=f.lower()
            if low.startswith('readme'):
                has['readme']=True
                try: readme_text+=open(fp,errors='replace').read()+'\n'
                except: pass
            if low in ('dockerfile','docker-compose.yml','docker-compose.yaml','compose.yml','compose.yaml'): has['docker']=True
            if low in ('package.json','requirements.txt','pyproject.toml','cargo.toml','go.mod','pubspec.yaml','package.swift','build.gradle','pom.xml','project.godot','setup.py','environment.yml','pipfile','gemfile','platformio.ini','cmakelists.txt','makefile','anchor.toml'):
                has['manifest']=True; manifests.append(rp)
            if low in ('.env.example','.env.sample','.env.template','env.example','.env.local.example','example.env'): has['env_example']=True
            if low in ('.env','.env.local','.env.production','.env.development') : env_files.append(rp)
            if low=='.gitignore': has['gitignore']=True
            if low.startswith('license'): has['license']=True
            if low in ('.eslintrc','.eslintrc.js','.eslintrc.json','.eslintrc.cjs','eslint.config.js','eslint.config.mjs','.prettierrc','.oxlintrc.json','ruff.toml','.flake8','biome.json','.pylintrc','setup.cfg','tsconfig.json'): has['lint']=True
            if '.github/workflows' in rp.replace('\\','/') or low in ('.gitlab-ci.yml','.travis.yml','vercel.json','netlify.toml','render.yaml','fly.toml','railway.json','railway.toml','app.yaml','procfile'): has['ci']=True
            if re.search(r'(^|/)(tests?|__tests__|spec)(/|$)',rp.replace('\\','/')) or re.search(r'(test_.*\.py|.*_test\.(py|go)|.*\.(test|spec)\.(js|ts|jsx|tsx))$',low): has['tests']=True
            ext=os.path.splitext(low)[1]
            if ext in ('.png','.jpg','.jpeg','.gif','.svg','.mp3','.wav','.ogg','.mp4','.ttf','.otf','.woff','.woff2','.glb','.gltf','.fbx','.obj','.aseprite','.psd','.blend','.ico','.webp'): has['assets']+=1
            if ext=='.ipynb': has['notebooks']+=1
            if ext in CODE_EXT and not GEN_PAT.search(low):
                lang=CODE_EXT[ext]
                if lang=='TypeScript': has['ts']=True
                try:
                    with open(fp,errors='replace') as fh:
                        n=0; txt=[]
                        for line in fh:
                            if line.strip(): n+=1
                            txt.append(line)
                        content=''.join(txt)
                    # skip generated: very long lines
                    if sz>400_000 and lang in ('JavaScript','CSS','JSON','HTML'): continue
                    loc[lang]+=n; files[lang]+=1
                    if lang not in NONCODE and sz<2_000_000:
                        for m in SECRET_PAT.finditer(content):
                            secrets.append((rp,m.group(0)[:12]+'…'))
                except: pass
            elif ext in ('.env',) or low in ('.env','.env.local'):
                pass
    for ef in env_files:
        try:
            content=open(os.path.join(p,ef),errors='replace').read()
            if re.search(r'=\s*\S{16,}',content): secrets.append((ef,'env-file-with-values'))
        except: pass
    code_loc=sum(v for k,v in loc.items() if k not in NONCODE)
    r.update({'files_total':total_files,'vendored_files_committed':vendored_files,'vendored_dirs':sorted(x for x in vendored_dirs if x),'loc_by_lang':dict(loc.most_common()),'code_loc':code_loc,'code_files':sum(v for k,v in files.items() if k not in NONCODE),'big_files':big[:10],'secrets_found':secrets[:10],'env_files_committed':env_files,'has':has,'manifests':manifests[:8],'readme_len':len(readme_text),'readme_words':len(readme_text.split())})
    # LOC added during hackathon vs before (git diff stats on code files)
    try:
        first_during=None
        st=sh("git log --all --format='%H %aI' --reverse",p).strip().splitlines()
        during_hashes=[l.split()[0] for l in st if datetime.datetime.fromisoformat(l.split()[1])>=HACK_START]
        if during_hashes and len(during_hashes)<len(st):
            base=sh(f"git rev-parse --verify --quiet {during_hashes[0]}^",p).strip()
            if not base or 'fatal' in base: base='4b825dc642cb6eb9a060e54bf8d69288fbee4904'
            head=sh("git rev-parse HEAD",p).strip()
            ns=sh(f"git diff --numstat {base} {head}",p).strip().splitlines()
            add=0
            for l in ns:
                a,b,f=l.split('\t',2)
                if a=='-' or GEN_PAT.search(f.lower()) or any(x in f.split('/') for x in VENDOR_DIRS): continue
                ext=os.path.splitext(f.lower())[1]
                if ext in CODE_EXT and CODE_EXT[ext] not in NONCODE: add+=int(a)
            r['loc_added_during_hackathon']=add
        elif during_hashes: r['loc_added_during_hackathon']=code_loc
        else: r['loc_added_during_hackathon']=0
    except Exception as e: r['loc_added_during_hackathon']=None
    r['default_branch']=sh("git rev-parse --abbrev-ref HEAD",p).strip()
    r['branches']=len(sh("git branch -r",p).strip().splitlines())
    r['description_from_readme_head']=readme_text[:400].replace('\n',' ')
    return r
out=[]
for d in sorted(os.listdir(ROOT)):
    if not os.path.isdir(os.path.join(ROOT,d,'.git')) or d=='steelhacks.com': continue
    try: out.append(analyze(d))
    except Exception as e: out.append({'dir':d,'error':str(e)})
json.dump(out,open('/tmp/claude-0/-home-user-zjzcpj/56dabd89-f253-58f3-bb91-f7e189b0a41c/scratchpad/metrics.json','w'),indent=1,default=str)
for r in out:
    if 'error' in r: print('ERR',r); continue
    print(f"{r['repo']:<48} commits={r['commits_total']:>4} pre={r['commits_pre_hackathon']:>3} dur={r['commits_during_hackathon']:>3} auth={r['n_authors']} loc={r['code_loc']:>6} added={r['loc_added_during_hackathon']} readme_w={r['readme_words']:>5} tests={int(r['has']['tests'])} ci={int(r['has']['ci'])} vend={r['vendored_files_committed']} sec={len(r['secrets_found'])} first={str(r['first_commit'])[:10]}")
