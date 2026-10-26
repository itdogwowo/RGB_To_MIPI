#!/usr/bin/env python3
"""Copy real client symbols out of an existing .esch2 into a project's temp library.

Usage: mk_lib_entries.py <source.esch2> <target-project-dir>
Writes <target>/.tmp/library/symbol/<title>.json for every SYMBOL doc whose title is
in WANTED.
"""
import json, sys, os, collections

SRC, DIR = sys.argv[1], sys.argv[2]
WANTED = {"SSD2828QN4R", "SSD2828QN4", "DFR_DFR_Disp_Conn", "DFR_DFR_Touch_Conn"}

def parse(line):
    head, _, body = line.partition("||")
    if body.endswith("|"):
        body = body[:-1]
    try:
        h = json.loads(head)
    except Exception:
        return None, None
    try:
        b = json.loads(body) if body.strip() else {}
    except Exception:
        b = {}
    return h, b

lines = open(SRC, encoding="utf-8").read().split("\n")
docs, cur = [], None
for l in lines:
    h, b = parse(l)
    if h and h.get("type") == "DOCHEAD":
        cur = {"docType": b.get("docType"), "uuid": b.get("uuid"), "raw": []}
        docs.append(cur)
    if cur is not None:
        cur["raw"].append(l)

out = os.path.join(DIR, ".tmp", "library", "symbol")
os.makedirs(out, exist_ok=True)
made = []
for d in docs:
    if d["docType"] != "SYMBOL":
        continue
    meta = None
    for l in d["raw"]:
        if '"type":"META"' in l:
            meta = parse(l)[1]
            break
    title = (meta or {}).get("title", "")
    if title not in WANTED:
        continue
    # the real SSD symbol has pins spread over +/-150; the generic one uses +/-20
    if title == "SSD2828QN4":
        xs = []
        for l in d["raw"]:
            h, b = parse(l)
            if h and h.get("type") == "PIN":
                xs.append(abs(b.get("x", 0)))
        if not xs or max(xs) < 100:
            continue
    # normalise: canonical DOCHEAD + sequential tickets, otherwise the
    # embedder cannot split the document and tickets collide
    cleaned, t = [], 0
    for l in d["raw"]:
        h, b = parse(l)
        if not h:
            continue
        if h.get("type") == "DOCHEAD":
            cleaned.append(json.dumps({"type": "DOCHEAD"}, separators=(",", ":")) + "||" + json.dumps(b, separators=(",", ":")) + "|")
            continue
        t += 1
        h["ticket"] = t
        cleaned.append(json.dumps(h, separators=(",", ":")) + "||" + json.dumps(b, separators=(",", ":")) + "|")
    entry = {
        "name": title,
        "kind": "symbol",
        "title": title,
        "designator": "U" if "SSD" in title else "J",
        "description": "imported from client edit",
        "symbolUuid": d["uuid"],
        "symbolDoc": cleaned,
    }
    fn = os.path.join(out, title + ".json")
    json.dump(entry, open(fn, "w"), ensure_ascii=False)
    made.append((title, d["uuid"], len(d["raw"])))
for m in made:
    print("library entry:", m)
