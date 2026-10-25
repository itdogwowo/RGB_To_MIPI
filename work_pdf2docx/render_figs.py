import json, os, sys
sys.path.insert(0, "work_pdf2docx")
from render_pdf import open_doc, render_page

os.makedirs("work_pdf2docx/figs", exist_ok=True)
model = json.load(open("work_pdf2docx/doc_model.json"))
doc = open_doc()
manifest = []
for p in model:
    pageno = p["page"]
    k = 0
    for it in p["items"]:
        if it["type"] != "figure":
            continue
        k += 1
        b = it["bbox"]
        crop = [max(0, b[0] - 3), max(0, b[1] - 3), min(595, b[2] + 3), min(842, b[3] + 3)]
        out = f"work_pdf2docx/figs/p{pageno:03d}_{k}.png"
        ok, size = render_page(doc, pageno, dpi=200, crop=crop, out=out)
        manifest.append(dict(page=pageno, i=k, path=out, size=size, crop=crop,
                             caption=it.get("caption"), w_pt=crop[2]-crop[0]))
        print(out, size, it.get("caption"))
# tables that must be rendered as images
tab_manifest = []
for p in model:
    pageno = p["page"]
    k = 0
    for it in p["items"]:
        if it["type"] != "table" or not it.get("render_as_image"):
            continue
        k += 1
        b = it["bbox"]
        crop = [max(0, b[0] - 3), max(0, b[1] - 3), min(595, b[2] + 3), min(842, b[3] + 3)]
        out = f"work_pdf2docx/figs/tbl_p{pageno:03d}_{k}.png"
        ok, size = render_page(doc, pageno, dpi=200, crop=crop, out=out)
        tab_manifest.append(dict(page=pageno, k=k, path=out, size=size, crop=crop,
                                 bbox=b))
        print("TABLE-IMG", out, size)
json.dump(tab_manifest, open("work_pdf2docx/tables_img_manifest.json", "w"), indent=1, ensure_ascii=False)
json.dump(manifest, open("work_pdf2docx/figs_manifest.json", "w"), indent=1, ensure_ascii=False)
print("figures:", len(manifest))
