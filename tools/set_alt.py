#!/usr/bin/env python3
"""Set alt text on figures. Usage: python3 -I tools/set_alt.py <alt-map.json>
The map is {"P000010-stem-1": "description", ...}. Alt text lives only in the asset record;
the site builder puts it into the page."""
import json, pathlib, sys, datetime
BANK = pathlib.Path(__file__).resolve().parent.parent / "bank"
alts = json.loads(pathlib.Path(sys.argv[1]).read_text())
done = set()
for pid in sorted({a.rsplit("-", 2)[0] for a in alts}):
    f = BANK / "problems" / pid[:4] / f"{pid}.json"
    p = json.loads(f.read_text())
    for a in p["assets"]:
        if a["id"] in alts and a["alt"] != alts[a["id"]]:
            a["alt"] = alts[a["id"]]; done.add(a["id"])
    p["updated"] = datetime.date.today().isoformat()
    f.write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n")
missing = set(alts) - done
print(f"Alt text set on {len(done)} figures." + (f" Not found or unchanged: {sorted(missing)}" if missing else ""))
