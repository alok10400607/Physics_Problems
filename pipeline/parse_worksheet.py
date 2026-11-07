"""DOCX worksheet -> structured question JSON.
Usage: python3 parse_worksheet.py <worksheet.docx> <chapter_code> <out_dir> "<chapter title>"
"""
import json, re, shutil, subprocess, sys, pathlib, tempfile

docx, chapter, out, title = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]), sys.argv[4]
out.mkdir(parents=True, exist_ok=True)
work = pathlib.Path(tempfile.mkdtemp(prefix=f"{chapter}-"))
md_path = work / "worksheet.md"
subprocess.run(["pandoc", docx, "-t", "markdown-smart-superscript-subscript",
                "--wrap=none", f"--extract-media={work}", "-o", str(md_path)], check=True)
md = md_path.read_text()

body, rest = md.split("\n# Answer Key", 1)
akey, hints = rest.split("\n# Hints & Solutions", 1) if "# Hints & Solutions" in rest else (rest, "")
warnings, fixes = [], []

IMG = re.compile(r'!\[[^\]]*\]\(([^)]+)\)(\{[^}]*\})?')
def unescape(s):
    s = re.sub(r'\\([\[\]()*_])', r'\1', s)
    return s.strip()

def fix_math(s, qid):
    # sin/cos/tan typed as plain letters inside equations -> proper functions
    def fx(m):
        inner = m.group(1)
        new = re.sub(r'(?<![\\a-zA-Z])(sin|cos|tan|cot|sec|ln|log)(?=[\s(\\{a-zA-Z0-9])', r'\\\1 ', inner)
        new = re.sub(r'(?<=[A-Za-z0-9])(?<!\\)(sin|cos|tan)(?=[(\\0-9])', r'\\\1 ', new)
        if new != inner: fixes.append(f"{qid}: `{inner}` -> `{new}`")
        return "$" + new + "$"
    return re.sub(r'\$([^$]+)\$', fx, s)

def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

# ---- Answer key ----
answers = {}
for line in akey.splitlines():
    if not re.match(r'\s*Q\d+', line): continue
    for qn, val in re.findall(r'Q(\d+)\s+(.*?)(?=\s{2,}Q\d+|\s*$)', line.strip()):
        answers[int(qn)] = unescape(val.strip())

# ---- Hints & solutions ----
hint_map = {}
cur = None
for line in hints.splitlines():
    m = re.match(r'\*\*Q(\d+)\*\*\s*\*([^*]+)\*', line)
    if m: cur = (int(m.group(1)), m.group(2).strip().lower()); continue
    if line.startswith("**") and line.endswith("**"): cur = None; continue
    if cur and line.strip():
        hint_map.setdefault(cur[0], {}).setdefault(cur[1], []).append(line.strip())

# ---- Questions ----
subtopics, questions = [], []
section, q = None, None
figs_dir = out / "figures"; figs_dir.mkdir(exist_ok=True)
for old in figs_dir.glob(f"{chapter}-*"): old.unlink()

def copy_img(src, name):
    src = pathlib.Path(src.replace("../", "/")) if not pathlib.Path(src).exists() else pathlib.Path(src)
    dst = figs_dir / f"{name}{src.suffix}"
    shutil.copy(src, dst); return f"figures/{dst.name}"

def finish(q):
    if not q: return
    text_lines, opt_lines = [], []
    for ln in q["_lines"]:
        (opt_lines if re.match(r'\\\([A-D]\\\)', ln) else text_lines).append(ln)
    text = "\n\n".join(text_lines)
    figs = []
    for i, m in enumerate(IMG.finditer(text), 1):
        figs.append(copy_img(m.group(1), f"{q['id']}-fig{i}"))
    text = IMG.sub("", text)
    tags = re.findall(r'\\\[([^\]]*?)\\\]', text)
    text = re.sub(r'\\\[[^\]]*?\\\]\s*', '', text, count=len(tags))
    level = 1; source = None
    for t in tags:
        if re.fullmatch(r'L\d', t): level = int(t[1])
        else: source = t
    opts = {}
    if opt_lines:
        joined = " ".join(opt_lines)
        parts = re.split(r'(?:\\\(|\()([A-D])(?:\\\)|\))\s', joined)
        for k, v in zip(parts[1::2], parts[2::2]):
            m = IMG.search(v)
            opts[k] = {"image": copy_img(m.group(1), f"{q['id']}-opt{k}")} if m else fix_math(unescape(v), q['id'])
    ans = answers.get(q["n"])
    if len(opts) == 4: qtype = "mcq"
    elif opts: qtype = "mcq"; warnings.append(f"Q{q['n']}: has {len(opts)} options (expected 4)")
    elif ans and re.fullmatch(r'-?\d+(\.\d+)?', ans): qtype = "numerical"
    else: qtype = "subjective"
    rec = {"id": q["id"], "number": q["n"], "chapter": chapter, "subtopic": section["code"],
           "type": qtype, "level": level, "source": source,
           "question": fix_math(unescape(text), q["id"]), "figures": figs}
    if opts: rec["options"] = opts
    rec["answer"] = fix_math(ans, q["id"]) if ans else None
    for kind, lines in hint_map.get(q["n"], {}).items():
        rec[slug(kind).replace("-", "_")] = fix_math("\n\n".join(lines), q["id"])
    questions.append(rec)

for line in body.splitlines():
    if line.startswith("## "):
        finish(q); q = None
        name = unescape(line[3:])
        section = {"code": f"{chapter}.{len(subtopics)+1:02d}", "name": name}
        subtopics.append(section); continue
    m = re.match(r'(\d+)\.\s+(.*)', line)
    if m and section:
        finish(q)
        n = int(m.group(1))
        q = {"n": n, "id": f"{chapter}-Q{n:03d}", "_lines": [m.group(2)]}
        continue
    if q and line.strip(): q["_lines"].append(line.strip())
finish(q)

preamble = body.split("\n## ", 1)[0]
note = " ".join(l.strip().strip("*") for l in preamble.splitlines() if l.strip()) or None
for s in subtopics: s["count"] = sum(1 for x in questions if x["subtopic"] == s["code"])
data = {"chapter": chapter, "title": title,
        "note": note,
        "subtopics": subtopics, "questions": questions}
(out / f"{chapter}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
(work / "parse_log.json").write_text(json.dumps({"warnings": warnings, "fixes": fixes}, indent=2))
print(f"{len(questions)} questions, {len(subtopics)} subtopics, {len(answers)} answers, {len(hint_map)} hints")
print("warnings:", *warnings, sep="\n  ")
print("math fixes:", *fixes, sep="\n  ")
