#!/usr/bin/env python3
"""Load the topic list from TopicCode_v2.xlsx into bank/topics.json.
Usage: python3 -I tools/load_topics.py bank/sources/TopicCode_v2.xlsx
Keeps codes as 4-digit strings (CCSS). Existing topics that are no longer in the sheet are kept and
marked 'retired' (codes are never reused), and the script reports them."""
import json, pathlib, sys, openpyxl
BANK = pathlib.Path(__file__).resolve().parent.parent / "bank"
wb = openpyxl.load_workbook(sys.argv[1], data_only=True)
ws = wb["TopicCode"]
head = [c.value for c in ws[1]]
col = {h: i for i, h in enumerate(head)}
topics = []
for r in ws.iter_rows(min_row=2, values_only=True):
    if not r[col["Code"]]: continue
    code = str(r[col["Code"]]).strip().zfill(4)
    old = [o.strip().zfill(4) for o in str(r[col["Old code(s)"]] or "").replace(";", ",").split(",") if o.strip()]
    topics.append({"code": code, "chapter_code": code[:2], "chapter": r[col["Chapter"]], "name": r[col["Subtopic"]],
                   "covers": r[col["What it covers"]], "old_codes": old,
                   "syllabus_note": r[col["Syllabus note (2026)"]], "status": "active"})
codes = [t["code"] for t in topics]
dup = {c for c in codes if codes.count(c) > 1}
if dup: sys.exit(f"Duplicate codes in the sheet: {sorted(dup)}")
path = BANK / "topics.json"
prev = json.loads(path.read_text()) if path.exists() else []
retired = [dict(t, status="retired") for t in prev if str(t["code"]).zfill(4) not in codes and t.get("status") != "provisional"]
path.write_text(json.dumps(topics + retired, indent=2, ensure_ascii=False) + "\n")
print(f"{len(topics)} topics in {len({t['chapter_code'] for t in topics})} chapters written to bank/topics.json"
      + (f"; {len(retired)} earlier codes kept as retired" if retired else ""))
