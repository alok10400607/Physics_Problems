#!/usr/bin/env python3
"""Import a reviewed DOCX worksheet into the problem bank.

    python3 -I tools/import_docx.py <worksheet.docx> <topic-map.json> --check
        Pre-flight only. Prints the report and writes nothing.
    python3 -I tools/import_docx.py <worksheet.docx> <topic-map.json> --write
        Imports (refuses if any blocking issue remains).

Options: --report <file.json> saves the report; --force re-imports a file already logged.
Rules are in docs/worksheet-contract.md and docs/maths-style.md.
"""
import argparse, datetime, difflib, hashlib, json, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BANK = ROOT / "bank"
TODAY = datetime.date.today().isoformat()

ap = argparse.ArgumentParser()
ap.add_argument("docx"); ap.add_argument("topic_map")
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--check", action="store_true"); g.add_argument("--write", action="store_true")
ap.add_argument("--report"); ap.add_argument("--force", action="store_true")
args = ap.parse_args()

docx = pathlib.Path(args.docx).resolve()
tmap = json.loads(pathlib.Path(args.topic_map).read_text())
blocking, warnings, fixes = [], [], []
def block(msg): blocking.append(msg)
def warn(msg): warnings.append(msg)

# ---------- convert ----------
work = pathlib.Path(tempfile.mkdtemp(prefix="import-"))
subprocess.run(["pandoc", str(docx), "-t", "markdown-smart-superscript-subscript", "--wrap=none",
                f"--extract-media={work}", "-o", str(work / "w.md")], check=True)
md = (work / "w.md").read_text()
xml = subprocess.run(["unzip", "-p", str(docx), "word/document.xml"], capture_output=True, text=True).stdout
if "ProgID=\"Equation" in xml or "MathType" in xml:
    block("The file contains MathType or old Equation Editor objects, which cannot be read. Retype them with Word's equation editor.")

if "\n# Answer Key" not in md:
    block("No 'Answer Key' heading found.")
    body, rest = md, ""
else:
    body, rest = md.split("\n# Answer Key", 1)
akey, hints_md = rest.split("\n# Hints & Solutions", 1) if "# Hints & Solutions" in rest else (rest, "")
preamble = body.split("\n## ", 1)[0]
note = " ".join(l.strip().strip("*") for l in preamble.splitlines() if l.strip() and not l.startswith("#")) or None

# ---------- helpers ----------
IMG = re.compile(r'!\[[^\]]*\]\(([^)]+)\)(\{[^}]*\})?')
TAG = re.compile(r'\\\[([^\]]+?)\\\]')
SRC = re.compile(r'^(JEE Main|AIEEE|IIT-JEE|JEE Advanced|NEET|AIPMT|AIIMS)(?:\s+(\d{4}))?(?:,\s*(\d{1,2})\s+([A-Z][a-z]{2}))?(?:,\s*Shift\s*(\d))?(?:\s*\(([A-Za-z -]+)\))?$')
MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
EXAM_RELEVANCE = {"JEE Main": "JEE Main", "AIEEE": "JEE Main", "IIT-JEE": "JEE Advanced", "JEE Advanced": "JEE Advanced", "NEET": "NEET", "AIPMT": "NEET", "AIIMS": "NEET"}
UNICODE_MATH = re.compile(r'[ρ√²³¹⁰⁴⁵⁶⁷⁸⁹⁻×−→≤≥≈∝πωθαβγλμσφΔΣΩ°]')

def unescape(s):
    return re.sub(r'\\([\[\]()*_$])', r'\1', s).strip()

UNI_TEX = {"µ": "\\mu ", "μ": "\\mu ", "¼": "\\frac{1}{4}", "½": "\\frac{1}{2}", "¾": "\\frac{3}{4}",
           "×": "\\times ", "−": "-", "°": "^{\\circ}", "π": "\\pi ", "θ": "\\theta ", "ω": "\\omega ",
           "α": "\\alpha ", "β": "\\beta ", "λ": "\\lambda ", "Δ": "\\Delta ", "≤": "\\le ", "≥": "\\ge "}

def unescape_text(s):
    """Remove Markdown escapes outside equations (inside them the backslashes are LaTeX)."""
    parts = re.split(r'(\$\$[\s\S]+?\$\$|\$[^$]+\$)', s)
    return "".join(x if x.startswith("$") else re.sub(r'\\([\[\]()*_#>`~-])', r'\1', x) for x in parts).strip()

def fix_math(s, where):
    def fx(m):
        inner = m.group(1)
        new = re.sub(r'(?<![\\a-zA-Z])(sin|cos|tan|cot|sec|cosec|ln|log)(?=[\s(\\{a-zA-Z0-9])', r'\\\1 ', inner)
        new = re.sub(r'(?<=[A-Za-z0-9])(?<!\\)(sin|cos|tan)(?=[(\\0-9])', r'\\\1 ', new)
        for u, tex in UNI_TEX.items(): new = new.replace(u, tex)
        if new != inner: fixes.append(f"{where}: `{inner}` → `{new}`")
        return "$" + new + "$"
    return re.sub(r'\$([^$]+)\$', fx, s)

def style_scan(s, where):
    outside = re.sub(r'\$[^$]*\$', '', s)
    inside = "".join(re.findall(r'\$([^$]*)\$', s))
    if UNICODE_MATH.search(inside): warn(f"{where}: Unicode symbols inside an equation ({''.join(sorted(set(UNICODE_MATH.findall(inside))))})")
    if UNICODE_MATH.search(outside) or re.search(r'\b[a-zA-Z]\s*=\s*[-0-9]', outside):
        return True  # maths typed as plain text
    return False

def parse_one(t):
    m = SRC.match(t.strip())
    if not m: return None
    exam, year, day, mon, shift, mode = m.groups()
    if day and (not year or mon not in MONTHS): return None
    date = f"{year}-{MONTHS[mon]:02d}-{int(day):02d}" if day else None
    rec = {"kind": "exam", "exam": exam, "date": date, "shift": int(shift) if shift else None, "mode": mode, "raw": t.strip()}
    if year: rec["year"] = int(year)
    return rec

def parse_source(t):
    """One tag may hold several sources separated by ';'. Returns a list, or None if any part is not a source."""
    parts = [parse_one(x) for x in t.split(";")]
    return parts if all(parts) else None

def norm(s):
    s = IMG.sub("", s); s = re.sub(r'asset:\S+', '', s)
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

def chash(stem, options):
    return hashlib.sha256((norm(stem) + "|" + "|".join(norm(options[k]) for k in sorted(options))).encode()).hexdigest()[:16]

# ---------- answer key ----------
answers = {}
for line in akey.splitlines():
    line = line.replace("**", "").replace("|", "  ")
    if not re.match(r'\s*Q\d+', line): continue
    for qn, val in re.findall(r'Q(\d+)\s+(.*?)(?=\s{2,}Q\d+|\s*$)', line.strip()):
        n = int(qn)
        if n in answers: block(f"Q{n}: appears twice in the Answer Key")
        answers[n] = unescape(val.strip())

# ---------- hints & solutions ----------
extra = {}
cur = None
for line in hints_md.splitlines():
    m = re.match(r'\*\*Q(\d+)\*\*\s*\*([^*]+)\*', line)
    if m: cur = (int(m.group(1)), m.group(2).strip().lower()); continue
    if line.startswith("**") and line.rstrip().endswith("**"): cur = None; continue
    if cur and line.strip(): extra.setdefault(cur[0], {}).setdefault(cur[1], []).append(line.strip())

# ---------- questions ----------
sections, questions, section, q = [], [], None, None
plain_math = []

def finish(q):
    if not q: return
    n, where = q["n"], f"Q{q['n']}"
    text_lines, opt_lines = [], []
    OPT = r'(?:\\\(|\()[A-F](?:\\\)|\))'
    lines = []
    for ln in q["lines"]:
        m = re.match(r'^((?:!\[[^\]]*\]\([^)]*\)(?:\{[^}]*\})?\s*)+)(' + OPT + r'.*)$', ln)
        lines += [m.group(1).strip(), m.group(2)] if m else [ln]
    for ln in lines:
        (opt_lines if re.match(OPT, ln) else text_lines).append(ln)
    text = "\n\n".join(text_lines)
    # tags
    level, srcs, pid = None, [], None
    for t in TAG.findall(text):
        if re.fullmatch(r'L[1-6]', t): level = t
        elif re.fullmatch(r'P\d{6}', t): pid = t
        elif parse_source(t): srcs.extend(parse_source(t))
        else: warn(f"{where}: unrecognised tag [{t}] left in the text")
    text = TAG.sub(lambda m: "" if (re.fullmatch(r'L[1-6]|P\d{6}', m.group(1)) or parse_source(m.group(1))) else m.group(0), text)
    # figures in the stem, kept in place
    figs = []
    def stem_img(m):
        figs.append({"src": m.group(1), "role": "stem", "seq": len(figs) + 1})
        return f"![](asset:{{ID}}-stem-{len(figs)})"
    text = IMG.sub(stem_img, text)
    stem = fix_math(unescape(text), where)
    stem = re.sub(r'\s+\n', '\n', stem).strip()
    # options
    opts = {}
    if opt_lines:
        joined = " ".join(opt_lines)
        fixed = re.sub(r'(?<![\w(\\$])([A-D])\)(?=\s)', r'(\1)', joined)
        if fixed != joined: fixes.append(f"{where}: option label written without '(' (e.g. 'B)') read as '(B)'"); joined = fixed
        parts = re.split(r'(?:\\\(|\()([A-F])(?:\\\)|\))\s*', joined)
        for k, v in zip(parts[1::2], parts[2::2]):
            m = IMG.search(v)
            if m:
                figs.append({"src": m.group(1), "role": "option", "key": k})
                opts[k] = f"![](asset:{{ID}}-opt-{k})"
            else:
                opts[k] = fix_math(unescape(v), f"{where} option {k}")
    if opts and all(not v.strip() for v in opts.values()):
        opts = {k: f"Graph ({k}) in the figure" for k in opts}
        warn(f"{where}: the four options are labels on one combined figure; consider splitting it into one picture per option")
    for k, v in opts.items():
        if not v.strip(): block(f"{where}: option {k} is empty")
    # answer
    raw = answers.get(n)
    if raw is None: block(f"{where}: no entry in the Answer Key")
    if opts:
        if len(opts) != 4: block(f"{where}: has {len(opts)} options; MCQs need exactly 4")
        compact = re.sub(r'[\s,;&$]|and', '', raw or "")
        if raw and "$" in raw and re.fullmatch(r'[A-D]+', compact): fixes.append(f"{where}: answer '{raw}' typed in an equation read as {compact}")
        keys = list(compact) if re.fullmatch(r'[A-D]+', compact) else [raw or ""]
        if raw is not None and not all(re.fullmatch(r'[A-D]', k) for k in keys):
            block(f"{where}: MCQ answer '{raw}' is not a letter A–D")
        qtype = "mcq_multi" if len(keys) > 1 else "mcq_single"
        answer = {"keys": keys}
    elif raw is not None and re.fullmatch(r'-?\d+', raw):
        qtype, answer = "integer", {"value": int(raw)}
    elif raw is not None and re.fullmatch(r'-?\d*\.\d+', raw):
        qtype, answer = "numerical", {"value": float(raw), "tolerance": 0.01}
    elif raw is not None and (mu := re.fullmatch(r'(-?\d+(?:\.\d+)?)\s*(m|cm|mm|km|s|ms|h|min|m/s|cm/s|km/h|m/s2|m/s²|m/s\^2|N|kN|J|kJ|W|kW|hp|kg|g|rad|rad/s|rad/s²|rev|Hz|°|%|N/m)', raw.strip())):
        v = float(mu.group(1)); unit = mu.group(2).replace("m/s2", "m/s²").replace("m/s^2", "m/s²")
        qtype, answer = ("integer" if v.is_integer() and "." not in mu.group(1) else "numerical"), {"value": int(v) if v.is_integer() and "." not in mu.group(1) else v, "unit": unit}
        if qtype == "numerical": answer["tolerance"] = 0.01
    else:
        qtype, answer = "subjective", {"text": fix_math(raw or "", f"{where} answer")}
    if len(set(opts.values())) < len(opts): block(f"{where}: two options are identical")
    # style
    for label, s in [("stem", stem), *[(f"option {k}", v) for k, v in opts.items()]]:
        if style_scan(s, f"{where} {label}") and where not in plain_math: plain_math.append(where)
    if not srcs: pass
    if not level: pass
    # worksheet hints
    sol = {}
    for kind, lines in extra.get(n, {}).items():
        txt = fix_math(unescape_text("\n\n".join(lines)), f"{where} {kind}")
        if kind == "hint": sol.setdefault("hints", []).append(txt)
        elif kind in ("think further", "extension"): sol["extension"] = txt
        elif kind in ("solution", "full solution", "worked solution"): sol["conventional"] = txt
        else: warn(f"{where}: solution entry '{kind}' kept as extension text"); sol["extension"] = txt
    questions.append({"n": n, "pid": pid, "section": section, "type": qtype, "stem": stem, "options": opts,
                      "answer": answer, "level": level, "sources": srcs, "figs": figs, "sol": sol})

for line in body.splitlines():
    if line.startswith("## "):
        finish(q); q = None
        title = unescape(line[3:])
        code = tmap["sections"].get(title)
        if code is not None: code = str(code).zfill(4)
        if code is None: block(f"Section '{title}' is not in the topic map {args.topic_map}")
        section = {"title": title, "topic_code": code}
        sections.append(section); continue
    m = re.match(r'(\d+)\.\s+(.*)', line)
    if m and section:
        finish(q); q = {"n": int(m.group(1)), "lines": [m.group(2)]}; continue
    if q and line.strip(): q["lines"].append(line.strip())
finish(q)

# ---------- whole-file checks ----------
nums = [x["n"] for x in questions]
if not questions: block("No numbered questions found under Heading 2 sections.")
for i, n in enumerate(nums, 1):
    if n != i: block(f"Question numbering breaks at Q{n} (expected Q{i})"); break
for n in sorted(set(answers) - set(nums)): block(f"Answer Key has Q{n}, but there is no such question")
topics = {t["code"]: t for t in json.loads((BANK / "topics.json").read_text())}
prov = []
for s in sections:
    if s["topic_code"] is not None and s["topic_code"] not in topics: block(f"Topic code {s['topic_code']} ('{s['title']}') is not in bank/topics.json")
    elif s["topic_code"] in topics and topics[s["topic_code"]]["status"] == "provisional": prov.append(str(s["topic_code"]))
    elif s["topic_code"] in topics and topics[s["topic_code"]]["status"] != "active": block(f"Topic code {s['topic_code']} ('{s['title']}') is {topics[s['topic_code']]['status']}")
if prov: warn(f"Topic codes {', '.join(prov)} are provisional until the TopicCode_v2 list is loaded")
no_src = [f"Q{x['n']}" for x in questions if not x["sources"]]
no_lvl = [f"Q{x['n']}" for x in questions if not x["level"]]
if no_src: warn(f"{len(no_src)} questions have no source tag and will be marked rights 'unverified': {', '.join(no_src)}")
if no_lvl: warn(f"{len(no_lvl)} questions have no level tag: {', '.join(no_lvl)}")
if plain_math: warn(f"{len(plain_math)} questions have maths typed as plain text instead of equations (fix during solution writing): {', '.join(plain_math)}")

# figures
try:
    from PIL import Image
except ImportError:
    Image = None
for x in questions:
    for f in x["figs"]:
        p = pathlib.Path(f["src"])
        cand = [p, work / "media" / p.name]
        p = next((c for c in cand if c.exists()), None)
        if not p: block(f"Q{x['n']}: figure {f['src']} is missing from the file"); continue
        f["path"] = p
        ext = p.suffix.lower().lstrip(".")
        if ext in ("emf", "wmf"):
            out = subprocess.run(["soffice", "--headless", "--convert-to", "png", "--outdir", str(p.parent), str(p)], capture_output=True)
            png = p.with_suffix(".png")
            if not png.exists(): block(f"Q{x['n']}: figure {p.name} is in {ext.upper()} format and could not be converted"); continue
            f["path"], ext = png, "png"
        f["format"] = "jpg" if ext == "jpeg" else ext
        if Image and f["format"] in ("png", "jpg", "webp"):
            subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "trim_figures.py"), "--file", str(f["path"])], check=False, capture_output=True)
            with Image.open(f["path"]) as im: f["w"], f["h"] = im.size
            if f["w"] < 600: f["lowres"] = True
        else:
            f["w"] = f["h"] = 0
low = [f"Q{x['n']}" for x in questions if any(f.get("lowres") for f in x["figs"])]
if low: warn(f"{len(low)} questions have figures narrower than 600 px (marked needs_redraw): {', '.join(low)}")

# formulas: render every one with the site's KaTeX
fields = []
for x in questions:
    fields += [(f"Q{x['n']} stem", x["stem"])] + [(f"Q{x['n']} option {k}", v) for k, v in x["options"].items()]
    if "text" in x["answer"]: fields.append((f"Q{x['n']} answer", x["answer"]["text"]))
    for k, v in x["sol"].items():
        for s in (v if isinstance(v, list) else [v]): fields.append((f"Q{x['n']} {k}", s))
res = subprocess.run(["node", str(ROOT / "tools" / "katex_check.js")], input=json.dumps(fields), capture_output=True, text=True)
if res.returncode not in (0, 1): block("The formula checker failed to run: " + res.stderr[-300:])
for e in json.loads(res.stdout or "[]"): block(f"{e['where']}: formula does not render: {e['tex']} ({e['error']})")

# ---------- duplicates ----------
existing = {}
for f in (BANK / "problems").rglob("P*.json"):
    p = json.loads(f.read_text())
    if p["status"] != "retired": existing[p["id"]] = p
for x in questions:
    x["hash"] = chash(x["stem"], x["options"])
    x["norm"] = norm(x["stem"]) + " " + " ".join(norm(v) for v in x["options"].values())
dups = []
ex_norm = {pid: (p["content_hash"], norm(p["stem"]) + " " + " ".join(norm(v) for v in p.get("options", {}).values())) for pid, p in existing.items()}
for i, x in enumerate(questions):
    if x["pid"]: continue
    for pid, (h, txt) in ex_norm.items():
        r = 1.0 if h == x["hash"] else difflib.SequenceMatcher(None, x["norm"], txt).ratio() if difflib.SequenceMatcher(None, x["norm"], txt).quick_ratio() > 0.85 else 0
        if r > 0.9: dups.append({"question": f"Q{x['n']}", "matches": pid, "similarity": round(r, 3)})
    for y in questions[:i]:
        sm = difflib.SequenceMatcher(None, x["norm"], y["norm"])
        if sm.quick_ratio() > 0.85 and sm.ratio() > 0.9:
            dups.append({"question": f"Q{x['n']}", "matches": f"Q{y['n']} (same worksheet)", "similarity": round(sm.ratio(), 3)})
for d in dups: warn(f"{d['question']}: possible duplicate of {d['matches']} (similarity {d['similarity']})")

# updates (questions carrying an ID tag)
updates = [x for x in questions if x["pid"]]
for x in updates:
    if x["pid"] not in existing: block(f"Q{x['n']}: tagged [{x['pid']}] but no such problem in the bank")

# ---------- report ----------
sha = hashlib.sha256(docx.read_bytes()).hexdigest()
logged = [json.loads(f.read_text()) for f in (BANK / "imports").glob("*.json")]
if any(l.get("sha256") == sha for l in logged) and not args.force:
    block("This exact file has already been imported (see bank/imports/). Use --force only if that is intended.")
types = {}
for x in questions: types[x["type"]] = types.get(x["type"], 0) + 1
report = {"file": docx.name, "sha256": sha, "collection": tmap["collection"], "questions": len(questions),
          "new": len(questions) - len(updates), "updates": len(updates), "types": types,
          "sections": [{"topic_code": s["topic_code"], "title": s["title"], "count": sum(1 for x in questions if x["section"] is s)} for s in sections],
          "figures": sum(len(x["figs"]) for x in questions), "blocking": blocking, "warnings": warnings,
          "auto_fixes": fixes, "duplicates": dups}

def show(r):
    print(f"\n{r['file']}: {r['questions']} questions ({r['new']} new, {r['updates']} updates), {r['figures']} figures, types {r['types']}")
    for s in r["sections"]: print(f"  {s['topic_code']}  {s['title']}  ({s['count']})")
    print(f"\nBLOCKING ({len(blocking)})" if blocking else "\nBLOCKING: none")
    for b in blocking: print("  ✗", b)
    print(f"\nWARNINGS ({len(warnings)})")
    for w in warnings: print("  !", w)
    print(f"\nAUTO-FIXES ({len(fixes)})")
    for f in fixes: print("  ~", f)

if args.check or blocking:
    show(report)
    if args.report: pathlib.Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    if args.write and blocking: print("\nNothing written: fix the blocking items first."); sys.exit(1)
    sys.exit(1 if blocking else 0)

# ---------- write ----------
if (BANK / "collections" / f"{tmap['collection']}.json").exists() and not updates:
    print(f"Nothing written: collection {tmap['collection']} already exists. Re-import a worksheet carrying ID tags to update it."); sys.exit(1)
reg = json.loads((BANK / "registry.json").read_text())
created, updated = [], []

def asset_records(x, pid):
    out = []
    for f in x["figs"]:
        aid = f"{pid}-stem-{f['seq']}" if f["role"] == "stem" else f"{pid}-opt-{f['key']}"
        shard = pid[:4]
        dest = BANK / "assets" / shard / f"{aid}.{f['format']}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(f["path"], dest)
        rec = {"id": aid, "role": f["role"], "file": f"{shard}/{dest.name}", "format": f["format"],
               "width": f.get("w", 0), "height": f.get("h", 0), "alt": "", "origin": "docx",
               "needs_redraw": bool(f.get("lowres"))}
        if f["role"] == "option": rec["option_key"] = f["key"]
        out.append(rec)
    return out

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

collection = {"id": tmap["collection"], "kind": "worksheet", "title": tmap["title"], "chapter_code": tmap.get("chapter_code"),
              "note": note, "source_file": docx.name, "sections": [{"topic_code": s["topic_code"], "title": s["title"], "problems": []} for s in sections]}

for x in questions:
    if x["pid"]:
        pid = x["pid"]; old = existing[pid]
        new_fields = {"stem": x["stem"].replace("{ID}", pid), "options": {k: v.replace("{ID}", pid) for k, v in x["options"].items()}, "answer": x["answer"]}
        changed = [k for k, v in new_fields.items() if old.get(k, {} if k == "options" else None) != v]
        if changed:
            major = "answer" in changed or "options" in changed or (re.sub(r'\D', '', old["stem"]) != re.sub(r'\D', '', new_fields["stem"]))
            old.update(new_fields); old["version"] += 1; old["updated"] = TODAY
            old["content_hash"] = chash(old["stem"], old.get("options", {}))
            if major and old["status"] in ("ai_solved", "reviewed", "published"):
                old["status"] = "ai_tagged"
                sp = BANK / "solutions" / pid[:4] / f"{pid}.json"
                if sp.exists():
                    s = json.loads(sp.read_text()); s["status"] = "draft"
                    s.setdefault("check", {}).setdefault("issues", []).append(f"Problem changed (version {old['version']}): re-solve and re-check")
                    write_json(sp, s)
            write_json(BANK / "problems" / pid[:4] / f"{pid}.json", old)
            updated.append({"id": pid, "fields": changed, "major": major})
    else:
        pid = f"P{reg['next_problem_id']:06d}"; reg["next_problem_id"] += 1
        exams = sorted({EXAM_RELEVANCE[s["exam"]] for s in x["sources"]})
        rec = {"id": pid, "status": "imported", "version": 1, "type": x["type"], "topic_code": x["section"]["topic_code"],
               "concepts": [], "exams": exams,
               "difficulty": {"worksheet": x["level"], "ai": None, "ai_scores": None, "ai_reason": None, "ai_confidence": None, "expert": None},
               "time_estimate_s": None, "passage_id": None, "stem": x["stem"].replace("{ID}", pid)}
        if x["options"]: rec["options"] = {k: v.replace("{ID}", pid) for k, v in x["options"].items()}
        rec.update({"answer": x["answer"],
                    "sources": [{"kind": "worksheet", "ref": docx.stem, "qno": x["n"]}] + x["sources"],
                    "assets": asset_records(x, pid),
                    "rights": "past-paper" if x["sources"] else "unverified",
                    "content_hash": x["hash"], "duplicate_of": None, "variant_of": None, "created": TODAY, "updated": TODAY})
        write_json(BANK / "problems" / pid[:4] / f"{pid}.json", rec)
        if x["sol"]:
            write_json(BANK / "solutions" / pid[:4] / f"{pid}.json",
                       {"id": pid, "problem_version": 1, "status": "draft", "hints": x["sol"].get("hints", []),
                        "worded": None, "conventional": x["sol"].get("conventional"), "mistakes": [], "distractors": {},
                        "extension": x["sol"].get("extension"), "check": {"issues": []},
                        "generated_by": {"author": "worksheet", "model": None, "prompt_version": None, "date": TODAY},
                        "reviewed_by": None})
        created.append(pid)
    for cs, s in zip(collection["sections"], sections):
        if x["section"] is s: cs["problems"].append(pid)

write_json(BANK / "collections" / f"{tmap['collection']}.json", collection)
(BANK / "registry.json").write_text(json.dumps(reg, indent=2) + "\n")
report.update({"created_ids": created, "updated": updated, "date": TODAY})
write_json(BANK / "imports" / f"{TODAY}-{tmap['collection']}.json", report)
show(report)
print(f"\nWritten: {len(created)} new problems ({created[0] if created else '-'} to {created[-1] if created else '-'}), {len(updated)} updated.")
