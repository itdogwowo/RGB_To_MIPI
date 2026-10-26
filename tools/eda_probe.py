"""Probe an EasyEDA Pro .esch2/.epcb2 file and print a structural summary.

Usage: python3 eda_probe.py <file> [--bom] [--nets] [--docs]
"""
import json, sys, collections, re

def parse_lines(path):
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            head, sep, body = line.partition("||")
            if body.endswith("|"):
                body = body[:-1]
            try:
                h = json.loads(head)
            except Exception:
                continue
            try:
                b = json.loads(body) if body.strip() else {}
            except Exception:
                b = {}
            recs.append((h, b, line))
    return recs

def docs_of(recs):
    docs, cur = [], None
    for h, b, line in recs:
        if h.get("type") == "DOCHEAD":
            cur = {"docType": b.get("docType"), "uuid": b.get("uuid"), "items": []}
            docs.append(cur)
        if cur is not None:
            cur["items"].append((h, b))
    return docs

def summarize(path, show_bom=False, show_nets=False):
    recs = parse_lines(path)
    docs = docs_of(recs)
    types = collections.Counter(h.get("type") for h, b, _ in recs)
    print(f"# {path}")
    print(f"records={len(recs)} documents={len(docs)}")
    print("doc types:", dict(collections.Counter(d["docType"] for d in docs)))
    print("record types:", dict(types.most_common(20)))

    for d in docs:
        if d["docType"] != "SCH_PAGE":
            continue
        title = next((b.get("title") for h, b in d["items"] if h.get("type") == "META"), "")
        comps, attrs, labels, flags, texts = [], collections.defaultdict(dict), [], [], []
        for h, b in d["items"]:
            t = h.get("type")
            if t == "COMPONENT":
                comps.append(h.get("id"))
                attrs[h.get("id")]["_body"] = b
            elif t == "ATTR":
                pid = b.get("parentId")
                k = b.get("key")
                if k in ("Designator", "Device", "Value", "Name", "Footprint", "Supplier Part"):
                    attrs[pid][k] = b.get("value")
            elif t == "NETLABEL":
                labels.append(b.get("value") or b.get("text"))
            elif t == "NETFLAG":
                flags.append(b.get("value") or b.get("text"))
            elif t == "TEXT":
                texts.append(b.get("value") or b.get("text"))
        print(f"\n== SCH_PAGE '{title}' uuid={d['uuid']} components={len(comps)} "
              f"netlabels={len(labels)} netflags={len(flags)}")
        if show_bom:
            rows = []
            for cid in comps:
                a = attrs.get(cid, {})
                rows.append((a.get("Designator", "?"), a.get("Value", ""), a.get("Name", ""),
                             a.get("Device", ""), a.get("Footprint", "")))
            rows.sort(key=lambda r: (len(r[0]), r[0]))
            for r in rows:
                print(f"  {r[0]:<8} {r[1]:<18} {r[2]:<28} {r[3][:40]:<40} {r[4][:30]}")
        if show_nets:
            names = sorted(set(filter(None, labels + flags)))
            print("  nets:", ", ".join(names))

if __name__ == "__main__":
    path = sys.argv[1]
    summarize(path, show_bom="--bom" in sys.argv, show_nets="--nets" in sys.argv)
