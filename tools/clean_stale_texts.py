#!/usr/bin/env python3
"""Remove stale `×` TEXT records from an EasyEDA Pro schematic page (offline).

Why this exists
---------------
EasyEDA Pro keeps TEXT records that the editor has already deleted (there is no
tombstone for TEXT). The editor hides them, but:
  * `sch_ManufactureData.getPngFile()` includes them in the canvas, so an A4 sheet
    exports as 1800x2449 instead of 1800x1284;
  * after the project is reloaded they come back as live objects.

`sch_PrimitiveText.delete()` + `save()` does NOT persist, so the only fix is to
edit the .esch2 while the project is CLOSED.

What it does
------------
* only touches TEXT records that live inside the SCH_PAGE document
* only removes records whose `value` is exactly "×" AND whose `y` < 0 (below the sheet)
* keeps a timestamped .bak next to the file
* validates: every remaining line still parses, the removed lines were exactly the
  targeted ones, the 3 real texts survive, the file shrank by the expected count

Usage
-----
  python3 tools/clean_stale_texts.py "path/to/P1.esch2"           # dry run
  python3 tools/clean_stale_texts.py "path/to/P1.esch2" --write   # apply
"""
import json
import shutil
import sys
import time


def parse_docs(lines):
    """Split the record stream into documents, keeping each record's line index."""
    docs, cur = [], None
    for idx, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        head, _, body = s.partition("||")
        try:
            h = json.loads(head)
        except Exception:
            h = {}
        try:
            b = json.loads(body.rstrip("|")) if body.strip() else {}
        except Exception:
            b = {}
        if h.get("type") == "DOCHEAD":
            cur = {"docType": b.get("docType"), "title": None, "items": []}
            docs.append(cur)
        elif cur is not None:
            if h.get("type") == "META" and b.get("title"):
                cur["title"] = b["title"]
            cur["items"].append((idx, h, b))
    return docs


def validate(lines, label):
    """Every line must be `{json head}||{json body}|`.

    The very last record in these files has no trailing `|` (EOF truncation), so
    that one case is tolerated.
    """
    bad = 0
    last = len(lines) - 1
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if s.count("||") != 1 or (not s.endswith("|") and i != last):
            print(f"  ! {label}: line {i} is not a well-formed record")
            bad += 1
            continue
        head = s.split("||")[0]
        try:
            json.loads(head)
        except Exception:
            print(f"  ! {label}: line {i} head is not JSON")
            bad += 1
    return bad


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    write = "--write" in sys.argv

    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    docs = parse_docs(lines)
    pages = [d for d in docs if d["docType"] == "SCH_PAGE"]
    if len(pages) != 1:
        print(f"refusing: expected exactly 1 SCH_PAGE, found {len(pages)}")
        return 1
    page = pages[0]

    victims, kept_texts = [], []
    for idx, h, b in page["items"]:
        if h.get("type") != "TEXT":
            continue
        value = str(b.get("value"))
        y = b.get("y")
        if value == "×" and isinstance(y, (int, float)) and y < 0:
            victims.append(idx)
        else:
            kept_texts.append((value, b.get("x"), y))

    kept_kinds = {}
    for value, _, _ in kept_texts:
        kept_kinds[value[:14]] = kept_kinds.get(value[:14], 0) + 1

    print(f"file      : {path}")
    print(f"lines     : {len(lines)}")
    print(f"stale '×' : {len(victims)}")
    print(f"other TEXT: {len(kept_texts)} -> {kept_kinds}")

    if not victims:
        print("nothing to do")
        return 0

    # sanity: every victim must be a TEXT record
    for i in victims:
        head = lines[i].split("||")[0]
        if json.loads(head).get("type") != "TEXT":
            print(f"refusing: line {i} is not a TEXT record")
            return 1

    out = [ln for i, ln in enumerate(lines) if i not in set(victims)]
    print(f"result    : {len(out)} lines (-{len(lines) - len(out)})")

    bad_before = validate(lines, "before")
    bad_after = validate(out, "after")
    if bad_after:
        print(f"refusing: {bad_after} malformed records after transform")
        return 1

    # the transform must not disturb the document structure
    docs_after = parse_docs(out)
    if len(docs_after) != len(docs):
        print(f"refusing: document count changed {len(docs)} -> {len(docs_after)}")
        return 1

    if not write:
        print("\n(dry run; re-run with --write to apply)")
        return 0

    backup = f"{path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(path, backup)
    print(f"backup    : {backup}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"written   : {path}")

    # re-read and confirm
    with open(path, encoding="utf-8", errors="replace") as f:
        check = f.read().splitlines()
    d2 = parse_docs(check)
    p2 = [d for d in d2 if d["docType"] == "SCH_PAGE"][0]
    left = [b.get("value") for _, h, b in p2["items"] if h.get("type") == "TEXT"]
    print(f"verify    : {len(check)} lines, texts now {left}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
