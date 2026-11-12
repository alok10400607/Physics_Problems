#!/usr/bin/env python3
"""Import a solutions DOCX (written with the jee-worksheet-solutions skill) into bank/solutions/.

    python3 -I tools/import_solutions.py <solutions.docx> --check
        Pre-flight only. Prints the report and writes nothing.
    python3 -I tools/import_solutions.py <solutions.docx> --write
        Imports (refuses if any blocking issue remains).

Options: --report <file.json> saves the report; --force re-imports a file already logged;
         --replace overwrites solutions written by Claude (llm) or an expert that are not yet reviewed.
         --only <Q list or topic code>, e.g. --only 0305 or --only 1-10, imports part of the file.

Layout of the file (docs/worksheet-contract.md, "Solutions files"):
    # <subtopic name>
    ## Q<n> · <short title>                      (an ID tag [P000123] here or in the ID line wins)
    ID <solution id> · Code <topic> · Worksheet <collection>_v<k> Q<n>
    ### Problem            compared with the bank; not stored
    ### Hint               -> hints
    ### Think it through   -> worded
    ### Another way: …     -> appended to worded under its own title (also "No-pen route")
    ### Why the other options are there -> distractors (one line per wrong option), else appended to worded
    ### Worked solution    -> conventional (figures become <problem>-sol-<n> assets)
    ### Answer             checked against the answer key; a disagreement is flagged, the key is never changed
    ### Watch out          -> mistakes (one per bullet). A final "Notes: …" line is reported, not stored.
"""
import argparse, datetime, difflib, hashlib, json, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BANK = ROOT / "bank"
TODAY = datetime.date.today().isoformat()

ap = argparse.ArgumentParser()
ap.add_argument("docx")
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--check", action="store_true"); g.add_argument("--write", action="store_true")
ap.add_argument("--report"); ap.add_argument("--force", action="store_true"); ap.add_argument("--replace", action="store_true")
ap.add_argument("--only")
args = ap.parse_args()

docx = pathlib.Path(args.docx).resolve()
blocking, warnings, fixes = [], [], []
def block(m): blocking.append(m)
def warn(m): warnings.append(m)

# ---------- convert ----------
work = pathlib.Path(tempfile.mkdtemp(prefix="solimport-"))
subprocess.run(["pandoc", str(docx), "-t", "markdown-smart-superscript-subscript", "--wrap=none",
                f"--extract-media={work}", "-o", str(work / "s.md")], check=True)
md = (work / "s.md").read_text()
xml = subprocess.run(["unzip", "-p", str(docx), "word/document.xml"], capture_output=True, text=True).stdout
if "ProgID=\"Equation" in xml or "MathType" in xml:
    block("The file contains MathType or old Equation Editor objects, which cannot be read. Retype them with Word's equation editor.")

# ---------- text helpers ----------
IMG = re.compile(r'!\[[^\]]*\]\(([^)]+)\)(\{[^}]*\})?')
MATH = re.compile(r'(\$\$[\s\S]+?\$\$|\$[^$]+\$)')
UNITS = ("km/h|m/s\\^\\{2\\}|m/s|cm/s|rad/s|N/m|kg|km|cm|mm|ms|min|rad|rev|Hz|kN|kJ|kW|m|s|h|N|J|W|g")
UNI_TEX = {"µ": "\\mu ", "μ": "\\mu ", "½": "\\frac{1}{2}", "¼": "\\frac{1}{4}", "¾": "\\frac{3}{4}", "×": "\\times ",
           "−": "-", "°": "^{\\circ}", "π": "\\pi ", "θ": "\\theta ", "ω": "\\omega ", "α": "\\alpha ", "β": "\\beta ",
           "λ": "\\lambda ", "Δ": "\\Delta ", "≤": "\\le ", "≥": "\\ge ", "≈": "\\approx ", "√": "\\sqrt "}

def tidy_tex(t):
    """Bring Word's equations to docs/maths-style.md."""
    o = t
    t = re.sub(r'\{\\overrightarrow\{([^{}]+)\}\}', r'\\vec{\1}', t)
    t = re.sub(r'\\overrightarrow\{([^{}]+)\}', r'\\vec{\1}', t)
    t = re.sub(r'\\widehat\{\\imath\}', r'\\ihat ', t); t = re.sub(r'\\widehat\{\\jmath\}', r'\\jhat ', t)
    t = re.sub(r'\\widehat\{k\}', r'\\khat ', t)
    # units after a number, a closing brace or bracket:  2\ cm  ->  2\unit{cm}
    t = re.sub(r'\\mspace\{(\d+)mu\}', r'\\mkern\1mu ', t)          # KaTeX has \mkern, not \mspace
    t = re.sub(r'(?:(?<=[\d}\)\]])|(?<=\\pi))\s*\\ (' + UNITS + r')(?![A-Za-z])', lambda m: "\\unit{" + m.group(1).replace("\\^\\{2\\}", "^{2}") + "}", t)
    # words typed inside an equation:  \ for\ half\ a\ revolution  ->  \text{ for half a revolution}
    def words(m):
        w = m.group(0).replace("\\ ", " ")
        return "\\text{" + w + "}" if re.search(r'[A-Za-z]{3,}', w) else m.group(0)
    t = re.sub(r'(?:\\ [A-Za-z]+(?:/[A-Za-z]+)?)+(?:\\ )?', words, t)
    t = re.sub(r'(?<![\\a-zA-Z])(sin|cos|tan|cot|sec|ln|log)(?=[\s(\\{0-9])', r'\\\1 ', t)
    for u, tex in UNI_TEX.items(): t = t.replace(u, tex)
    return t, t != o

def tidy(s, where):
    """Markdown from pandoc -> the bank's Markdown: unescape outside maths, tidy inside."""
    out = []
    for part in MATH.split(s):
        if part.startswith("$"):
            dd = part.startswith("$$")
            inner = part[2:-2] if dd else part[1:-1]
            new, ch = tidy_tex(inner)
            if ch: fixes.append(f"{where}: `{inner.strip()[:70]}` → `{new.strip()[:70]}`")
            out.append(("$$" if dd else "$") + new + ("$$" if dd else "$"))
        else:
            part = re.sub(r'\s*`<!-- -->`\{=html\}\s*', '\n\n', part)
            part = re.sub(r'\\([\[\]()*_#>`~\-$.!|])', r'\1', part)
            part = part.replace("\\\n", "\n")          # hard line break
            out.append(part)
    s = "".join(out)
    s = re.sub(r'^(\d+)\.\s{2,}', r'\1. ', s, flags=re.M)   # "1.  The tip…" -> "1. The tip…"
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()

def norm(s):
    s = IMG.sub("", s); s = re.sub(r'asset:\S+', '', s)
    s = re.sub(r'\\(frac|sqrt|left|right|text|mathrm|unit|times|quad)', ' ', s)
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

# ---------- parse ----------
preamble, *chunks = re.split(r'\n(?=# )', "\n" + md)
items = []
for ch in chunks:
    head, *rest = ch.split("\n", 1)
    subtopic = tidy(head[2:], "heading")
    for qblock in re.split(r'\n(?=## )', "\n" + (rest[0] if rest else ""))[1:]:
        qhead, *qrest = qblock.split("\n", 1)
        body = qrest[0] if qrest else ""
        m = re.match(r'##\s+Q(\d+)\s*[·.:-]?\s*(.*)', qhead)
        if not m: warn(f"Heading '{qhead[:60]}' is not 'Q<n> · title'; skipped"); continue
        n, title = int(m.group(1)), m.group(2)
        it = {"n": n, "title": tidy(re.sub(r'\\\[[^\]]*\\\]', '', title), f"Q{n} title"), "subtopic": subtopic,
              "pid": None, "code": None, "ref": None, "sections": [], "notes": None}
        tag = re.search(r'\[(P\d{6})\]', qhead + body.split("\n### ", 1)[0].replace("\\", ""))
        if tag: it["pid"] = tag.group(1)
        idl = re.search(r'^ID\s+(\S+)\s*·\s*Code\s+(\d{4})\s*·\s*Worksheet\s+(\S+)\s+Q(\d+)', body, re.M)
        if idl:
            it["sol_id"], it["code"], it["ref"], it["ref_q"] = idl.group(1), idl.group(2), idl.group(3), int(idl.group(4))
        for sec in re.split(r'\n(?=### )', "\n" + body)[1:]:
            sh, *sb = sec.split("\n", 1)
            it["sections"].append((sh[4:].strip(), (sb[0] if sb else "").strip()))
        items.append(it)

if not items: block("No '## Q<n> · title' questions found under '# subtopic' headings.")
if args.only:
    o = args.only
    if re.fullmatch(r'\d{4}', o): items = [x for x in items if x["code"] == o]
    else:
        keep = set()
        for part in o.split(","):
            a, _, b = part.partition("-"); keep |= set(range(int(a), int(b or a) + 1))
        items = [x for x in items if x["n"] in keep]

# ---------- bank ----------
problems = {}
for f in (BANK / "problems").rglob("P*.json"):
    p = json.loads(f.read_text()); problems[p["id"]] = p
collections = {f.stem: json.loads(f.read_text()) for f in (BANK / "collections").glob("*.json")}
topics = {t["code"]: t for t in json.loads((BANK / "topics.json").read_text())}

def by_number(coll, qno):
    c = collections.get(coll)
    if not c: return None
    for sec in c["sections"]:
        for pid in sec["problems"]:
            ws = next((s for s in problems[pid]["sources"] if s["kind"] == "worksheet"), None)
            if ws and ws["qno"] == qno: return pid
    return None

def problem_text(p):
    return p["stem"] + " " + " ".join(f"({k}) {v}" for k, v in sorted(p.get("options", {}).items()))

# ---------- each question ----------
KNOWN = ("problem", "hint", "think it through", "another way", "no-pen route", "why the other options are there",
         "worked solution", "answer", "watch out")
results, figures_total, notes_lines = [], 0, 0
seen_pids = {}
for it in items:
    where = f"Q{it['n']}"
    # match
    how = None
    pid = it["pid"]
    if pid:
        how = "tag"
        if pid not in problems: block(f"{where}: tagged [{pid}] but no such problem in the bank"); continue
    else:
        coll = re.sub(r'_v\d+$', '', it["ref"] or "")
        qno = it.get("ref_q", it["n"])
        if not it["ref"]: warn(f"{where}: no 'ID … · Worksheet …' line; matched by number within the file's collection")
        if not coll:
            cands = {re.sub(r'_v\d+$', '', x["ref"]) for x in items if x["ref"]}
            coll = cands.pop() if len(cands) == 1 else None
        pid = by_number(coll, qno) if coll else None
        how = "number"
        if not pid: block(f"{where}: no problem in collection {coll or '?'} with question number {qno}. Add an ID tag [P000123]."); continue
    if pid in seen_pids: block(f"{where}: matches {pid}, which {seen_pids[pid]} already matched"); continue
    seen_pids[pid] = where
    p = problems[pid]
    r = {"q": it["n"], "id": pid, "matched_by": how, "title": it["title"], "issues": []}
    if it["code"] and it["code"] != p["topic_code"]:
        r["issues"].append(f"solution file says topic {it['code']}, the bank has {p['topic_code']}")
        warn(f"{where} ({pid}): topic code {it['code']} in the solutions file, {p['topic_code']} in the bank")
    if p["status"] == "retired": block(f"{where}: {pid} is retired")

    secs = {}
    extra_worded = []
    for name, text in it["sections"]:
        key = name.lower()
        base = next((k for k in KNOWN if key.startswith(k)), None)
        if base in ("another way", "no-pen route"):
            extra_worded.append((name, text))
        elif base == "why the other options are there":
            secs["why"] = text
        elif base:
            if base in secs: warn(f"{where}: two '{name}' sections; the second is appended")
            secs[base] = (secs.get(base, "") + "\n\n" + text).strip()
        else:
            warn(f"{where}: unknown section '### {name}' appended to the worded solution")
            extra_worded.append((name, text))

    for need in ("problem", "hint", "think it through", "worked solution", "answer"):
        if not secs.get(need): r["issues"].append(f"no '{need.capitalize()}' section"); warn(f"{where} ({pid}): no '### {need.capitalize()}' section")

    # problem text agrees?
    if secs.get("problem"):
        a, b = norm(tidy(secs["problem"], where)), norm(problem_text(p))
        sim = difflib.SequenceMatcher(None, a, b).ratio()
        r["problem_similarity"] = round(sim, 3)
        if sim < 0.5:
            block(f"{where}: the Problem text does not match {pid} (similarity {sim:.2f}). Wrong question number? Add an ID tag.")
        elif sim < 0.9:
            diff = [d for d in difflib.ndiff(b.split(), a.split()) if d[0] in "+-"][:14]
            r["issues"].append(f"problem text differs from the bank (similarity {sim:.2f})")
            warn(f"{where} ({pid}): problem text differs from the bank (similarity {sim:.2f}): {' '.join(diff)}")

    # figures: number them across the whole solution in reading order
    figs = []
    def fig(m):
        figs.append(m.group(1))
        return f"![](asset:{pid}-sol-{len(figs)})"
    def sec(name): return tidy(IMG.sub(fig, secs.get(name, "")), f"{where} {name}") or None

    hint = sec("hint")
    worded = sec("think it through")
    for name, text in extra_worded:
        body = tidy(IMG.sub(fig, text), f"{where} {name}")
        worded = ((worded + "\n\n") if worded else "") + f"**{tidy(name, where)}.** " + body
    conventional = sec("worked solution")

    distractors = {}
    if secs.get("why"):
        why = tidy(secs["why"], f"{where} why")
        sentences = [x for x in re.split(r'(?<=[.!?])\s+(?=[A-Z])', why) if x.strip()]
        letters = [set(re.findall(r'\(([A-F])\)', x)) for x in sentences]
        if p.get("options") and all(len(l) == 1 for l in letters):   # one sentence per wrong option
            for x, l in zip(sentences, letters):
                k = l.pop(); distractors[k] = (distractors.get(k, "") + " " + x).strip()
        else:
            worded = ((worded + "\n\n") if worded else "") + "**Why the other options are there.** " + why
        if p.get("answer", {}).get("keys") and set(distractors) & set(p["answer"]["keys"]):
            warn(f"{where} ({pid}): 'Why the other options' explains the correct option {sorted(set(distractors) & set(p['answer']['keys']))}")

    mistakes, notes = [], None
    if secs.get("watch out"):
        wo = secs["watch out"]
        mn = re.search(r'\n\s*Notes:\s*(.+)$', wo, re.S)
        if mn: notes = mn.group(1).strip(); wo = wo[:mn.start()]
        for b in re.split(r'\n\s*(?:•|\\?-|\*)\s+', "\n" + wo):
            b = tidy(IMG.sub(fig, b), f"{where} watch out")
            if b: mistakes.append(b)
    if notes: notes_lines += 1; r["notes"] = notes

    # answer against the key
    ans = tidy(secs.get("answer", ""), f"{where} answer")
    key = p["answer"]
    agrees = None
    if ans:
        if "keys" in key:
            letters = re.findall(r'\(([A-F])\)', ans) or re.findall(r'^\s*([A-F])\b', ans)
            letters = sorted(set(letters))
            agrees = letters == sorted(key["keys"]) if letters else None
            if agrees is None: r["issues"].append(f"answer '{ans[:40]}' names no option")
        elif "value" in key:
            nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', re.sub(r'\$[^$]*\$', ' ', ans) or ans)]
            nums = nums or [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', ans)]
            tol = max(abs(key["value"]) * (key.get("tolerance") or 0.01), 1e-9)
            agrees = any(abs(v - key["value"]) <= tol for v in nums) if nums else None
        else:
            kn, an = norm(key.get("text", "")), norm(ans)
            knums = re.findall(r'\d+(?:\.\d+)?', kn)
            if kn and (kn in an or difflib.SequenceMatcher(None, kn, an).ratio() > 0.8 or (knums and len(kn) < 40 and all(x in an.split() for x in knums))):
                agrees = True
            else:
                agrees = None   # written answers: the reviewer compares them
        if agrees is False:
            r["issues"].append(f"answer disagrees with the key: solution '{ans[:60]}', key {json.dumps(key, ensure_ascii=False)[:80]}")
            warn(f"{where} ({pid}): ANSWER DISAGREES WITH THE KEY. Solution: {ans[:80]} | Key: {json.dumps(key, ensure_ascii=False)[:100]}")
        elif agrees is None:
            r["issues"].append("answer to be compared with the key by the reviewer")
    r["answer"] = ans; r["agrees"] = agrees

    # existing solution
    sp = BANK / "solutions" / pid[:4] / f"{pid}.json"
    old = json.loads(sp.read_text()) if sp.exists() else None
    if old:
        author = (old.get("generated_by") or {}).get("author")
        if old["status"] in ("reviewed", "published", "in_review"):
            block(f"{where}: {pid} already has {old['status']} solutions; they are not overwritten. Remove this question from the file, or retire the old solutions first.")
        elif author in ("llm", "expert") and (old.get("worded") or old.get("conventional")) and not args.replace:
            block(f"{where}: {pid} already has solutions written by {author} ({old['status']}). Use --replace to overwrite them.")
        r["replaces"] = f"{old['status']} by {author}" + (f"; its hint was: {old['hints'][0][:80]}" if old.get("hints") else "")

    figures_total += len(figs)
    hints = [hint] if hint else []
    complete = bool(hints and worded and conventional)
    status = "ai_solved" if complete and agrees is not False else "draft"
    issues = [x for x in r["issues"]]
    r.update({"status": status, "figures": len(figs)})
    r["record"] = {"id": pid, "problem_version": p["version"], "status": status, "hints": hints, "worded": worded,
                   "conventional": conventional, "mistakes": mistakes, "distractors": distractors, "extension": None,
                   "check": {"solved_answer": ans or None, "resolve_answer": None, "agrees_with_key": agrees, "issues": issues},
                   "generated_by": {"author": "worksheet", "model": None, "prompt_version": docx.stem, "date": TODAY},
                   "reviewed_by": None}
    r["figs"] = figs
    results.append(r)

# file-level: numbering and coverage
nums = [x["n"] for x in items]
dupn = sorted({n for n in nums if nums.count(n) > 1})
if dupn: block(f"Question numbers used twice: {', '.join('Q%d' % n for n in dupn)}")
colls = {re.sub(r'_v\d+$', '', x["ref"]) for x in items if x["ref"]}
for c in colls:
    if c in collections and not args.only:
        in_c = [pid for s in collections[c]["sections"] for pid in s["problems"]]
        missing = [pid for pid in in_c if pid not in seen_pids]
        if missing: warn(f"{len(missing)} problems of {c} have no solution in this file: {', '.join(missing)}")

# figures: find the files
for r in results:
    paths = []
    for src in r["figs"]:
        p = pathlib.Path(src)
        cand = [p, work / "media" / p.name]
        p = next((c for c in cand if c.exists()), None)
        if not p: block(f"Q{r['q']}: figure {src} is missing from the file"); paths.append(None); continue
        if p.suffix.lower() in (".emf", ".wmf"):
            subprocess.run(["soffice", "--headless", "--convert-to", "png", "--outdir", str(p.parent), str(p)], capture_output=True)
            p = p.with_suffix(".png")
            if not p.exists(): block(f"Q{r['q']}: figure {src} could not be converted"); paths.append(None); continue
        paths.append(p)
    r["fig_paths"] = paths

# formulas
fields = []
for r in results:
    rec = r["record"]
    for k in ("worded", "conventional"): fields.append((f"Q{r['q']} {k}", rec[k]))
    fields += [(f"Q{r['q']} hint", h) for h in rec["hints"]] + [(f"Q{r['q']} watch out", m) for m in rec["mistakes"]]
    fields += [(f"Q{r['q']} why ({k})", v) for k, v in rec["distractors"].items()]
res = subprocess.run(["node", str(ROOT / "tools" / "katex_check.js")], input=json.dumps(fields), capture_output=True, text=True)
try: bad = json.loads(res.stdout)
except ValueError: bad = []; block("The formula checker failed to run (run `npm ci` in tools/): " + res.stderr.strip()[-300:])
for e in bad: block(f"{e['where']}: formula does not render: {e['tex'][:90]} ({e['error']})")
plain = [f"Q{r['q']}" for r in results if re.search(r'\\(\(|\[)', (r['record']['conventional'] or ""))]
if plain: block(f"\\( or \\[ maths left in: {', '.join(plain)}")

# ---------- report ----------
sha = hashlib.sha256(docx.read_bytes()).hexdigest()
logged = [json.loads(f.read_text()) for f in (BANK / "imports").glob("*.json")]
if any(l.get("sha256") == sha for l in logged) and not args.force and not args.only:
    block("This exact file has already been imported (see bank/imports/). Use --force only if that is intended.")
disagree = [f"Q{r['q']} {r['id']}" for r in results if r["agrees"] is False]
to_compare = [f"Q{r['q']} {r['id']}" for r in results if r["agrees"] is None]
report = {"file": docx.name, "sha256": sha, "kind": "solutions", "questions": len(items), "matched": len(results),
          "matched_by": {k: sum(1 for r in results if r["matched_by"] == k) for k in ("tag", "number")},
          "status": {s: sum(1 for r in results if r["status"] == s) for s in ("ai_solved", "draft")},
          "figures": figures_total, "answers_disagree": disagree, "answers_to_compare": to_compare,
          "notes_lines_not_stored": notes_lines, "blocking": blocking, "warnings": warnings, "auto_fixes": fixes,
          "per_question": [{k: v for k, v in r.items() if k not in ("record", "figs", "fig_paths")} for r in results]}

def show():
    print(f"\n{docx.name}: {len(items)} solutions, {len(results)} matched "
          f"({report['matched_by']['tag']} by ID tag, {report['matched_by']['number']} by question number), {figures_total} figures")
    print(f"  would be saved as: {report['status']['ai_solved']} ai_solved, {report['status']['draft']} draft")
    print(f"  answers: {len(results) - len(disagree) - len(to_compare)} agree with the key, {len(disagree)} disagree, "
          f"{len(to_compare)} written answers for the reviewer to compare")
    print(f"\nBLOCKING ({len(blocking)})" if blocking else "\nBLOCKING: none")
    for b in blocking: print("  ✗", b)
    print(f"\nWARNINGS ({len(warnings)})")
    for w in warnings: print("  !", w)
    print(f"\nAUTO-FIXES ({len(fixes)} formulas brought to the maths style; see --report for the list)")
    for f in fixes[:8]: print("  ~", f)
    if notes_lines: print(f"\nNOT STORED: {notes_lines} 'Notes: Sec. …' lines (links to the revision notes; the bank has no field for them yet)")
    if figures_total: print(f"NEEDS ALT TEXT: {figures_total} solution figures (the file names them, but has no descriptions)")

if args.check or blocking:
    show()
    if args.report: pathlib.Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    if args.write and blocking: print("\nNothing written: fix the blocking items first."); sys.exit(1)
    sys.exit(1 if blocking else 0)

# ---------- write ----------
try:
    from PIL import Image
except ImportError:
    Image = None

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

for r in results:
    pid = r["id"]; p = problems[pid]
    keep = [a for a in p["assets"] if a["role"] != "solution"]
    old_sol = {a["id"]: a for a in p["assets"] if a["role"] == "solution"}
    for a in old_sol.values():
        (BANK / "assets" / a["file"]).unlink(missing_ok=True)
    recs = []
    for i, src in enumerate(r["fig_paths"], 1):
        aid = f"{pid}-sol-{i}"
        ext = src.suffix.lower().lstrip("."); ext = "jpg" if ext == "jpeg" else ext
        dest = BANK / "assets" / pid[:4] / f"{aid}.{ext}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)
        if Image and ext in ("png", "jpg", "webp"):
            subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "trim_figures.py"), "--file", str(dest)], capture_output=True)
            with Image.open(dest) as im: w, h = im.size
        else: w = h = 0
        prev = old_sol.get(aid)
        recs.append({"id": aid, "role": "solution", "file": f"{pid[:4]}/{dest.name}", "format": ext, "width": w, "height": h,
                     "alt": prev["alt"] if prev else "", "origin": "docx", "needs_redraw": bool(w and w < 600)})
    p["assets"] = keep + recs
    p["updated"] = TODAY
    write_json(BANK / "problems" / pid[:4] / f"{pid}.json", p)
    write_json(BANK / "solutions" / pid[:4] / f"{pid}.json", r["record"])

report["date"] = TODAY
tag = f"-{args.only.replace(',', '_')}" if args.only else ""
write_json(BANK / "imports" / f"{TODAY}-{docx.stem}{tag}.json", report)
show()
print(f"\nWritten: {len(results)} solution files, {figures_total} solution figures.")
