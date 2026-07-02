#!/usr/bin/env python3
"""
extract.py — offline docling parse of the raw contract corpus.

Walks THIS repo for every .pdf / .docx and runs docling over each, writing
per-document parse artifacts under artifacts/, mirroring the source folder tree:

    artifacts/<same/relative/path>/<source-filename>/
        content.md          # linearized document text
        docling.json        # structured DoclingDocument (export_to_dict)
        tables/000.csv ...   # one CSV per detected table (the rate matrices)

Idempotent: a document whose content.md already exists is skipped, so a crash
partway through the ~1000-doc corpus resumes cheaply and re-runs are incremental.

Run on the Mac mini (Apple Silicon → MPS acceleration is picked automatically):

    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python extract.py
    git add artifacts && git commit -m "docling artifacts" && git push

Then pull artifacts/ on the dev box. See EXTRACTION.md.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    PdfPipelineOptions,
    TableFormerMode,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

REPO = Path(__file__).resolve().parent
OUT = REPO / "artifacts"
SOURCE_EXTS = {".pdf", ".docx"}

# A PDF whose extracted text is shorter than this is treated as scanned / image-only
# (empty text layer) and re-run once with OCR. Keeps OCR (~5s/page) off the ~1000
# born-digital docs while still capturing the scanned ones.
MIN_CONTENT_CHARS = 30


def build_converter(*, ocr: bool) -> DocumentConverter:
    """A converter for PDF (+ DOCX). `ocr` toggles the slow OCR pass (PDF only)."""
    pdf = PdfPipelineOptions()
    pdf.do_ocr = ocr
    if ocr:
        # docling 2.108's default OCR (RapidOCR / torch) errors with
        # "Unsupported configuration: torch.PP-OCRv6.det.small". EasyOCR is the
        # reliable cross-platform engine; it downloads its models once.
        # force_full_page_ocr: image-only scans are a single full-page bitmap;
        # regional OCR skips them, so force OCR over the whole page.
        pdf.ocr_options = EasyOcrOptions(force_full_page_ocr=True)
    pdf.do_table_structure = True
    pdf.table_structure_options.mode = TableFormerMode.ACCURATE  # rate matrices matter
    # AUTO → MPS on Apple Silicon, CPU elsewhere. Same script runs anywhere.
    pdf.accelerator_options = AcceleratorOptions(device=AcceleratorDevice.AUTO)
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.DOCX],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf)},
    )


def artifact_dir(src: Path) -> Path:
    """artifacts/<relative dir>/<source filename incl. extension>/ — unambiguous."""
    rel = src.relative_to(REPO)
    return OUT / rel.parent / rel.name


def write_artifacts(adir: Path, doc, markdown: str) -> None:
    adir.mkdir(parents=True, exist_ok=True)
    (adir / "content.md").write_text(markdown, encoding="utf-8")
    (adir / "docling.json").write_text(
        json.dumps(doc.export_to_dict(), ensure_ascii=False), encoding="utf-8"
    )
    tables = getattr(doc, "tables", None) or []
    if tables:
        tdir = adir / "tables"
        tdir.mkdir(exist_ok=True)
        for i, table in enumerate(tables):
            # docling 2.x requires the owning doc to resolve table cell refs.
            table.export_to_dataframe(doc=doc).to_csv(tdir / f"{i:03d}.csv", index=False)


def find_sources() -> list[Path]:
    return sorted(
        p
        for p in REPO.rglob("*")
        if p.is_file()
        and p.suffix.lower() in SOURCE_EXTS
        and OUT not in p.parents
        and ".git" not in p.parts
    )


def main() -> int:
    sources = find_sources()
    total = len(sources)
    print(f"Found {total} source documents under {REPO}")

    conv = build_converter(ocr=False)
    ocr_conv: DocumentConverter | None = None
    done = skipped = failed = ocr_used = 0
    low_text: list[str] = []  # ended up with little/no text even after OCR — review these
    started = time.monotonic()

    for n, src in enumerate(sources, 1):
        adir = artifact_dir(src)
        # "Done" means a real extraction: an existing but near-empty content.md
        # (an image-only scan the previous run couldn't read) is re-attempted,
        # now with force-full-page OCR.
        existing = adir / "content.md"
        if existing.exists() and len(existing.read_text(encoding="utf-8").strip()) >= MIN_CONTENT_CHARS:
            skipped += 1
            continue
        rel = src.relative_to(REPO)
        try:
            doc = conv.convert(src).document
            md = doc.export_to_markdown()
            # Scanned/image PDF (empty text layer) → one OCR retry. Non-fatal:
            # if OCR errors we keep the non-OCR result rather than losing the doc.
            if src.suffix.lower() == ".pdf" and len(md.strip()) < MIN_CONTENT_CHARS:
                try:
                    if ocr_conv is None:
                        ocr_conv = build_converter(ocr=True)
                    ocr_doc = ocr_conv.convert(src).document
                    ocr_md = ocr_doc.export_to_markdown()
                    if len(ocr_md.strip()) > len(md.strip()):
                        doc, md = ocr_doc, ocr_md
                        ocr_used += 1
                except Exception as ocr_exc:
                    print(f"[{n}/{total}] warn OCR failed, keeping non-OCR text {rel}: {ocr_exc}",
                          file=sys.stderr)
                if len(md.strip()) < MIN_CONTENT_CHARS:
                    low_text.append(str(rel))
            write_artifacts(adir, doc, md)
            done += 1
            print(f"[{n}/{total}] ok   {rel}")
        except Exception as exc:  # unreadable/corrupt source: log and keep going
            failed += 1
            print(f"[{n}/{total}] FAIL {rel}: {exc}", file=sys.stderr)

    elapsed = time.monotonic() - started
    print(
        f"\nDone in {elapsed:.0f}s — extracted {done} (OCR {ocr_used}), "
        f"skipped {skipped}, failed {failed}."
    )
    if low_text:
        print(f"\n{len(low_text)} doc(s) still have little/no text (image-only or empty) "
              f"— review manually:")
        for p in low_text:
            print(f"  - {p}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
