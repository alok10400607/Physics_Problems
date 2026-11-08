#!/usr/bin/env python3
"""Import a CSV question list (JeeProblems layout) into the problem bank.

    python3 -I tools/import_csv.py <file.csv> --collection <ID> --title "<title>" --check
    python3 -I tools/import_csv.py <file.csv> --collection <ID> --title "<title>" --write

Columns (header names, any order; extra columns are ignored):
  Question, Option A, Option B, Option C, Option D   question text and options (an option may be an image file name)
  Answer                                             required: A–D (or AD for several), or a number, or text
  Topic Code                                         TopicCode_v2 code (e.g. 0211) or an old code listed in topics.json
  Figure                                             optional: image file name for the question
  ID, Exam, Year, Source                             optional: original row ID, exam name, year, free-text source
Images are looked up next to the CSV and in a 'figures' folder beside it.
Rules: docs/worksheet-contract.md (CSV section).
"""
import argparse, csv, datetime, difflib, hashlib, json, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BANK = ROOT / "bank"
TODAY = datetime.date.today().isoformat()
ap = argparse.ArgumentParser()
ap.add_argument("csv"); ap.add_argument("--collection", required=True); ap.add_argument("--title", required=True)
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--check", action="store_true"); g.add_argument("--write", action="store_true")
ap.add_argument("--report"); ap.add_argument("--force", action="store_true")
ap.add_argument("--codes", help='JSON file {"<ID or row number>": "<new 4-digit code>"} for rows whose old code maps to several new codes')
args = ap.parse_args()
src = pathlib.Path(args.csv).resolve()
blocking, warnings, fixes = [], [], []
block, warn = blocking.append, warnings.append

EXAM_RELEVANCE = {"JEE Main": "JEE Main", "AIEEE": "JEE Main", "IIT-JEE": "JEE Advanced", "JEE Advanced": "JEE Advanced",
                  "NEET": "NEET", "AIPMT": "NEET", "AIIMS": "NEET"}
UNI = re.compile(r'[ρ√²³¹⁰⁻×−→≤≥≈∝πωθαβγλμσφΔΣΩ°]')

def norm(s): return re.sub(r'[^a-z0-9]+', ' ', re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s).lower()).strip()
def chash(stem, opts): return hashlib.sha256((norm(stem) + "|" + "|".join(norm(opts[k]) for k in sorted(opts))).encode()).hexdigest()[:16]

topics = json.loads((BANK / "topics.json").read_text())
by_code = {t["code"]: t for t in topics}
overrides = json.loads(pathlib.Path(args.codes).read_text()) if args.codes else {}
by_old = {}
for t in topics:
    for o in t.get("old_codes", []): by_old.setdefault(o.zfill(4), []).append(t["code"])

with open(src, newline="", encoding="utf-8-sig") as fh:
    rows = list(csv.DictReader(fh))
if not rows: block("The CSV has no rows.")
cols = {c.strip().lower(): c for c in (rows[0].keys() if rows else [])}
def col(r, name): c = cols.get(name.lower()); return (r.get(c) or "").strip() if c else ""
for need in ["question", "option a", "option b", "option c", "option d", "answer", "topic code"]:
    if need not in cols: block(f"Column '{need.title()}' is missing" + (" — every question needs its answer" if need == "answer" else ""))

def find_image(name):
    for d in (src.parent, src.parent / "figures", src.parent / (src.stem + "_figures")):
        p = d / name
        if p.exists(): return p
    return None

qs = []
if not blocking:
    for i, r in enumerate(rows, 1):
        where = f"Row {i}" + (f" (ID {col(r, 'id')})" if col(r, "id") else "")
        stem = col(r, "question")
        if len(stem) < 10: block(f"{where}: question text is missing"); continue
        # year typed at the end of the question, e.g. "(2017)"
        year = col(r, "year")
        m = re.search(r'\s*\((\d{4})\)\s*$', stem)
        if m:
            stem = stem[:m.start()].rstrip(); year = year or m.group(1)
            fixes.append(f"{where}: year ({m.group(1)}) moved from the question text into the source")
        opts, figs = {}, []
        for k in "ABCD":
            v = col(r, f"option {k}")
            if not v: block(f"{where}: option {k} is empty"); continue
            if re.fullmatch(r'[\w .-]+\.(png|jpe?g|gif|svg)', v, re.I):
                p = find_image(v)
                if not p: block(f"{where}: option {k} image '{v}' not found next to the CSV or in figures/")
                figs.append({"role": "option", "key": k, "path": p, "name": v}); opts[k] = f"![](asset:{{ID}}-opt-{k})"
            else: opts[k] = v
        if col(r, "figure"):
            p = find_image(col(r, "figure"))
            if not p: block(f"{where}: figure '{col(r, 'figure')}' not found next to the CSV or in figures/")
            figs.insert(0, {"role": "stem", "seq": 1, "path": p, "name": col(r, "figure")}); stem = "![](asset:{ID}-stem-1)\n\n" + stem
        raw = col(r, "answer"); compact = re.sub(r'[\s,;&$]|and', '', raw)
        if not raw: block(f"{where}: no answer"); continue
        if re.fullmatch(r'[A-D]+', compact): qtype, answer = ("mcq_multi" if len(compact) > 1 else "mcq_single"), {"keys": list(compact)}
        else: block(f"{where}: answer '{raw}' is not a letter A–D for a four-option question"); continue
        code_raw = col(r, "topic code").zfill(4)
        ov = overrides.get(col(r, "id")) or overrides.get(str(i))
        if ov:
            ov = str(ov).zfill(4)
            if ov not in by_code or by_code[ov]["status"] != "active": block(f"{where}: chosen code {ov} is not an active TopicCode_v2 code"); continue
            code = ov; fixes.append(f"{where}: topic code {col(r, 'topic code')} set to {code} ({by_code[code]['name']}) from --codes")
        elif code_raw in by_code and by_code[code_raw]["status"] == "active" and len(col(r, "topic code")) == 4: code = code_raw
        elif code_raw in by_old and len(set(by_old[code_raw])) == 1:
            code = by_old[code_raw][0]; fixes.append(f"{where}: old topic code {col(r, 'topic code')} mapped to {code} ({by_code[code]['name']})")
        elif code_raw in by_old: block(f"{where}: old topic code {col(r, 'topic code')} maps to several new codes ({', '.join(sorted(set(by_old[code_raw])))}); choose one per question with --codes"); continue
        elif code_raw in by_code: code = code_raw
        else: block(f"{where}: topic code '{col(r, 'topic code')}' is not in TopicCode_v2 (new or old codes)"); continue
        if len(set(opts.values())) < len(opts): block(f"{where}: two options are identical")
        if UNI.search(stem + " ".join(opts.values())) and "$" not in stem: warn(f"{where}: maths typed as plain text (e.g. Unicode symbols); fix during solution writing")
        exam = col(r, "exam")
        sources = [{"kind": "csv", "ref": src.name, "qno": int(col(r, "id")) if col(r, "id").isdigit() else i}]
        if exam or year:
            s = {"kind": "exam" if exam else "csv", "raw": " ".join(x for x in [exam, year] if x)}
            if exam: s["exam"] = exam
            if year: s["year"] = int(year)
            if col(r, "source"): s["raw"] = col(r, "source")
            sources.append(s)
        qs.append({"row": i, "where": where, "type": qtype, "stem": stem, "options": opts, "answer": answer,
                   "code": code, "figs": figs, "sources": sources, "exam": exam, "hash": chash(stem, opts)})

# figures: size checks
try:
    from PIL import Image
except ImportError:
    Image = None
for q in qs:
    for f in q["figs"]:
        if not f["path"]: continue
        f["format"] = f["path"].suffix.lower().lstrip(".").replace("jpeg", "jpg")
        if Image and f["format"] in ("png", "jpg"):
            with Image.open(f["path"]) as im: f["w"], f["h"] = im.size
            if f["w"] < 600: f["lowres"] = True
        else: f["w"] = f["h"] = 0

# formulas
fields = [(q["where"], q["stem"]) for q in qs] + [(f"{q['where']} option {k}", v) for q in qs for k, v in q["options"].items()]
res = subprocess.run(["node", str(ROOT / "tools" / "katex_check.js")], input=json.dumps(fields), capture_output=True, text=True)
for e in json.loads(res.stdout or "[]"): block(f"{e['where']}: formula does not render: {e['tex']} ({e['error']})")

# duplicates: exact copies inside the file are merged (the copy with a figure is kept); near-copies and bank matches are reported
dups, keep = [], []
for q in qs:
    twin = next((k for k in keep if k["hash"] == q["hash"]), None)
    if twin:
        better, other = (q, twin) if (q["figs"] and not twin["figs"]) else (twin, q)
        better["sources"] += [s for s in other["sources"] if s not in better["sources"]]
        if better is q: keep[keep.index(twin)] = q
        fixes.append(f"{other['where']} is an exact copy of {better['where']}; kept one ({better['where']}{', which has the figure' if better['figs'] else ''})")
        continue
    keep.append(q)
existing = {}
for f in (BANK / "problems").rglob("P*.json"):
    p = json.loads(f.read_text())
    if p["status"] != "retired": existing[p["id"]] = p
for q in keep:
    t = norm(q["stem"]) + " " + " ".join(norm(v) for v in q["options"].values())
    for pid, p in existing.items():
        if p["content_hash"] == q["hash"]: dups.append((q["where"], pid, 1.0)); continue
        u = norm(p["stem"]) + " " + " ".join(norm(v) for v in p.get("options", {}).values())
        sm = difflib.SequenceMatcher(None, t, u)
        if sm.quick_ratio() > 0.85 and sm.ratio() > 0.9: dups.append((q["where"], pid, round(sm.ratio(), 3)))
for w, pid, r in dups: warn(f"{w}: possible duplicate of {pid} in the bank (similarity {r}); not imported until you decide")
dup_rows = {w for w, _, _ in dups}

sha = hashlib.sha256(src.read_bytes()).hexdigest()
if any(json.loads(f.read_text()).get("sha256") == sha for f in (BANK / "imports").glob("*.json")) and not args.force:
    block("This exact file has already been imported (see bank/imports/).")
if (BANK / "collections" / f"{args.collection}.json").exists(): block(f"Collection {args.collection} already exists; choose another --collection")
report = {"file": src.name, "sha256": sha, "collection": args.collection, "rows": len(rows), "to_import": len([q for q in keep if q["where"] not in dup_rows]),
          "blocking": blocking, "warnings": warnings, "auto_fixes": fixes, "duplicates": [{"row": w, "matches": p, "similarity": r} for w, p, r in dups]}
def show():
    print(f"\n{src.name}: {len(rows)} rows, {report['to_import']} to import")
    print(f"\nBLOCKING ({len(blocking)})" if blocking else "\nBLOCKING: none"); [print("  ✗", b) for b in blocking]
    print(f"\nWARNINGS ({len(warnings)})"); [print("  !", w) for w in warnings]
    print(f"\nAUTO-FIXES ({len(fixes)})"); [print("  ~", f) for f in fixes]
if args.check or blocking:
    show()
    if args.report: pathlib.Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(1 if blocking else 0)

# write
reg = json.loads((BANK / "registry.json").read_text())
sections, created = {}, []
for q in keep:
    if q["where"] in dup_rows: continue
    pid = f"P{reg['next_problem_id']:06d}"; reg["next_problem_id"] += 1
    assets = []
    for f in q["figs"]:
        aid = f"{pid}-stem-{f['seq']}" if f["role"] == "stem" else f"{pid}-opt-{f['key']}"
        dest = BANK / "assets" / pid[:4] / f"{aid}.{f['format']}"; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(f["path"], dest)
        subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "trim_figures.py"), "--file", str(dest)], capture_output=True)
        if Image and f["format"] in ("png", "jpg"):
            with Image.open(dest) as im: f["w"], f["h"] = im.size
        a = {"id": aid, "role": f["role"], "file": f"{pid[:4]}/{dest.name}", "format": f["format"], "width": f.get("w", 0),
             "height": f.get("h", 0), "alt": "", "origin": "csv", "needs_redraw": f.get("w", 0) < 600}
        if f["role"] == "option": a["option_key"] = f["key"]
        assets.append(a)
    rec = {"id": pid, "status": "imported", "version": 1, "type": q["type"], "topic_code": q["code"], "concepts": [],
           "exams": sorted({EXAM_RELEVANCE[q["exam"]]} if q["exam"] in EXAM_RELEVANCE else set()),
           "difficulty": {"worksheet": None, "ai": None, "ai_scores": None, "ai_reason": None, "ai_confidence": None, "expert": None},
           "time_estimate_s": None, "passage_id": None, "stem": q["stem"].replace("{ID}", pid),
           "options": {k: v.replace("{ID}", pid) for k, v in q["options"].items()}, "answer": q["answer"],
           "sources": q["sources"], "assets": assets, "rights": "past-paper" if q["exam"] else "unverified",
           "content_hash": q["hash"], "duplicate_of": None, "variant_of": None, "created": TODAY, "updated": TODAY}
    out = BANK / "problems" / pid[:4] / f"{pid}.json"; out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    sections.setdefault(q["code"], []).append(pid); created.append(pid)
coll = {"id": args.collection, "kind": "curated", "title": args.title, "chapter_code": None, "note": None, "source_file": src.name,
        "sections": [{"topic_code": c, "title": by_code[c]["name"], "problems": ids} for c, ids in sorted(sections.items())]}
(BANK / "collections" / f"{args.collection}.json").write_text(json.dumps(coll, indent=2, ensure_ascii=False) + "\n")
(BANK / "registry.json").write_text(json.dumps(reg, indent=2) + "\n")
report.update({"created_ids": created, "date": TODAY})
(BANK / "imports" / f"{TODAY}-{args.collection}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
show()
print(f"\nWritten: {len(created)} new problems ({created[0] if created else '-'} to {created[-1] if created else '-'}).")
