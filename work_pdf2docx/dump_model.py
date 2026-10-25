import json, sys
m = json.load(open("work_pdf2docx/doc_model.json"))
def render(words):
    s = ""
    for w in words:
        if w["text"] == "\n":
            s += " ⏎ "
        elif w.get("sub"):
            s += "_{" + w["text"] + "}"
        elif w.get("bold"):
            s += "**" + w["text"] + "**"
        else:
            s += w["text"]
    return s
pages = [int(a) for a in sys.argv[1:]] or range(1, len(m)+1)
for pg in pages:
    p = m[pg-1]
    print(f"\n########## PAGE {pg} ({len(p['items'])} items)")
    for it in p["items"]:
        if it["type"] == "heading":
            print(f"[H{it['level']}] {it['num']} {it['text']}")
        elif it["type"] == "para":
            print(("[•] " if it["bullet"] else "") + render(it["words"]))
        elif it["type"] == "caption":
            print("[CAP]", it["text"])
        elif it["type"] == "figure":
            print("[FIG]", [round(v) for v in it["bbox"]], "cap=", it["caption"])
        elif it["type"] == "table":
            print(f"[TABLE {it['nrows']}x{it['ncols']}] bbox={it['bbox']}")
            for r in range(it["nrows"]):
                row = []
                for c in range(it["ncols"]):
                    cell = it["cells"].get(f"{r},{c}")
                    if cell is None:
                        row.append("·")
                    else:
                        row.append(" ".join(" ".join(w["text"] for w in l) for l in cell["lines"])[:60])
                print("   | " + " | ".join(row))
