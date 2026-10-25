# SSD2828QN4 datasheet — AI-readable pack

A machine-first transcription of the Solomon Systech **SSD2828QN4** MIPI master bridge datasheet
(original: 168-page PDF, Rev 1.3, Mar 2013). Built so a model can answer questions about the chip
without parsing the PDF: clean Markdown, real tables, one file per chapter, and register data as CSV/JSON.

**Start here → `INDEX.md`** (chapter → file → PDF page) and **`quickref.md`** (distilled facts).

## Layout

| File | What it is | Size |
|---|---|---|
| `INDEX.md` | Chapter index with file names, PDF pages, token estimates | small |
| `quickref.md` | One-page distilled reference: specs, PLL, init sequence, register map | small |
| `datasheet.md` | The whole document as one Markdown file | ~169 KB |
| `sections/*.md` | One file per chapter (load only what you need) | 20 files |
| `registers.csv` | Flat table: offset, register, field, bits, type, reset, description, enum values | 66 registers / 250 fields |
| `registers.json` | Same data nested per register, with `enums[]` | |
| `pins.csv` | Pin function table (name, type, connect-to, description, unused handling) | 29 rows |
| `pinout.csv` | QFN pin number → net name | 68 pins |
| `timing.csv` | AC timing rows (symbol, parameter, min/typ/max, unit, table, page) | 54 rows |
| `figures/` + `figures.md` | Cropped diagrams (200 dpi PNG) with caption + page index | 65 images |
| `chunks.jsonl` | Retrieval chunks: `{id, section, pages, chars, text}` | 61 chunks |
| `source.json` | Provenance: source file, sha256, counts, conversion notes | small |

## Conventions

- `<!-- pdf:N -->` = the following content starts on page `N` of the original PDF.
- Headings keep the original numbering: `# 8 COMMAND TABLE`, `## 8.1 Register Description`,
  `### 8.1.2 RGB Interface Control Register 1`.
- Subscripts: `t_CLKH`, `f_PRE`, `T_MAX`.
- Figures: `![Figure 9-21: …](figures/p122_1.png)` — the caption is the alt text, the file is the crop.
- Bit-map tables are converted from the PDF's 16-column grid to `| Bits | Name | Type | Reset |` rows;
  the description table that follows the bitmap in the PDF gives the semantics and enum values.
- Register details are duplicated on purpose: prose in `sections/08_*` and rows in `registers.csv`
  (so a grep or a `csv` filter both work).

## How to use it

```bash
# find a register by mnemonic or address
grep -n "0xB9\|PCR" registers.csv | head

# pull every field with an enum table
python -c "import json;r=json.load(open('registers.json'));[print(x['offset'],f['bits'],f['name'],f['enums']) for x in r for f in x['fields'] if f['enums']]"

# read one chapter only
sed -n '1,200p' sections/09_configuration.md

# locate the PDF page for a topic
grep -rn "burst mode" sections/*.md | head
```

For a question about one topic, load `quickref.md` first, then the single chapter file.
The full `datasheet.md` is only needed for whole-document work.

## Provenance & fidelity

- Text, tables and figures are extracted from the PDF (pdfplumber + CoreGraphics rendering);
  nothing was rewritten by hand except this README, `quickref.md` and the section titles in `INDEX.md`.
- Cross-check: the longest paragraph of every content page (64 pages with >= 45 characters) is present
  verbatim in `datasheet.md` — 0 misses.
- Known losses: stacked fractions (flattened), a few column-rules-free tables (kept as images),
  and the original's own typos (kept as-is).

## Regenerating

```bash
python3 work_pdf2docx/extract.py        # PDF -> work_pdf2docx/doc_model.json
python3 work_pdf2docx/render_figs.py    # figure + table-image crops -> work_pdf2docx/figs
python3 work_pdf2docx/build_ai_docs.py  # -> ai_docs/ssd2828qn4
```

A human-facing Word version of the same document is at `../../SSD2828QN4_Datasheet_文件版.docx`
(repo root, 118 pages).
