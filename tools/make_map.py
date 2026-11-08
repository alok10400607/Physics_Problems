#!/usr/bin/env python3
"""Draft a worksheet's topic map from its Heading 2 sections.
Usage: python3 -I tools/make_map.py worksheets/03MSL_v2.docx [--collection 03MSL]
Exact matches with a subtopic name in the worksheet's chapter (taken from the first two digits of the
file name) are filled in; anything else is printed for a decision and left out of the map."""
import json, pathlib, re, subprocess, sys
BANK = pathlib.Path(__file__).resolve().parent.parent / "bank"
docx = pathlib.Path(sys.argv[1])
coll = sys.argv[sys.argv.index("--collection") + 1] if "--collection" in sys.argv else docx.stem.split("_")[0]
ch = coll[:2]
topics = [t for t in json.loads((BANK / "topics.json").read_text()) if t["chapter_code"] == ch and t["status"] == "active"]
if not topics: sys.exit(f"No active topics for chapter {ch}")
md = subprocess.run(["pandoc", str(docx), "-t", "markdown-smart", "--wrap=none"], capture_output=True, text=True, check=True).stdout
heads = [re.sub(r'\\(.)', r'\1', l[3:]).strip() for l in md.splitlines() if l.startswith("## ")]
byname = {t["name"].lower(): t["code"] for t in topics}
sections, unmatched = {}, []
for h in heads:
    code = byname.get(h.lower())
    if code: sections[h] = code
    else: unmatched.append(h)
m = {"collection": coll, "title": topics[0]["chapter"], "chapter_code": ch, "sections": sections}
out = BANK / "imports" / "maps" / f"{coll}.json"
if out.exists() and "--force" not in sys.argv: sys.exit(f"{out} already exists (use --force to overwrite)")
out.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")
print(f"{out.relative_to(BANK.parent)}: {len(sections)} of {len(heads)} sections mapped")
for h in unmatched: print(f"  needs a decision: '{h}' (chapter {ch} subtopics: {', '.join(t['code'] + ' ' + t['name'] for t in topics)})")
