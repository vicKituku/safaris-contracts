# Extraction handoff — run docling on the Mac mini

This repo holds the **raw contract corpus** (source of truth) plus an offline
**docling** parse script. The heavy parse runs on the Mac mini; the resulting
`artifacts/` folder is pushed back here and pulled on the dev box.

## On the Mac mini

```bash
git clone git@github.com:vicKituku/safaris-contracts.git   # (or: git pull)
cd safaris-contracts

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # docling + its deps (torch, pandas, …)

python extract.py                      # walks the corpus → writes artifacts/
```

- Apple Silicon is used automatically (MPS). First run downloads docling's models
  once, then caches them.
- **Resumable:** a document whose `artifacts/<path>/<file>/content.md` already
  exists is skipped, so a crash mid-run costs nothing to restart.
- Scanned/image PDFs (empty text layer) are auto-retried with OCR.

Then push the artifacts back:

```bash
git add artifacts requirements.txt extract.py EXTRACTION.md .gitignore
git commit -m "docling artifacts"
git push
```

## On the dev box (safaris-knowledgebase side)

```bash
cd Contracts && git pull      # pulls artifacts/
```

Each source document maps to:

```
artifacts/<same/relative/path>/<source-filename>/
    content.md          # linearized text
    docling.json        # structured parse
    tables/000.csv ...   # one CSV per detected table (rate matrices)
```

The downstream LLM extraction step (#5) reads `content.md` + `tables/*.csv` per
document and produces canonical rate JSON. docling output stays a **regenerable
intermediate** — re-run `extract.py` any time to reproduce it.
