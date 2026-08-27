# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Pack text extraction - the text LAYER of a pack PDF, nothing more.

Dependency note: PDF extraction uses ``pypdf`` (declared in the tender
manifest's dependencies), with ``pdfminer.six`` accepted as a fallback when
a bench happens to carry it instead. BOTH imports are lazy and guarded: on
a bench with neither library the module still imports and every PDF call
returns an explicit ``extractor-missing`` status instead of crashing - the
rest of the tender module is untouched. Plain-text input needs no library
at all.

Hard limits, by design (findings F-02 first pass, deterministic only):

- text layer only - NO OCR. A scanned/image-only pack returns status
  ``no-text-layer`` so the desk knows to capture by hand; the extractor
  never guesses at pixels.
- no network calls, no AI, no heuristics: bytes in, text out.

Result shape (plain dict, same for every path)::

    {"status": "ok" | "no-text-layer" | "extractor-missing" | "error",
     "text": str,          # "" unless status == "ok"
     "pages": int | None,  # PDF page count when known
     "extractor": "pypdf" | "pdfminer" | "plain-text" | None,
     "note": str}          # human-readable explanation, always present
"""

import io

PDF_MAGIC = b"%PDF"

EXTRACTOR_MISSING_NOTE = (
	"No PDF text-extraction library is available on this bench (pypdf is the "
	"declared dependency; pdfminer.six is accepted as a fallback). Install "
	"pypdf, or paste the pack text directly via pack_text."
)
NO_TEXT_LAYER_NOTE = (
	"This PDF has no extractable text layer (likely a scan). OCR is out of "
	"scope for the deterministic parser - capture the pack's returnables by "
	"hand, exactly as before."
)


def extract_pack_text(content, filename=None):
	"""Extracts the pack's text from raw file bytes (or str passthrough).

	``content`` is the file's raw bytes; a str is treated as already-
	extracted text (the pack_text path). ``filename`` is informational only
	- detection is by content (the %PDF magic), never by extension.
	"""
	if content is None:
		return _result("error", note="No file content provided.")
	if isinstance(content, str):
		text = content
		if not text.strip():
			return _result("error", note="The provided pack text is empty.")
		return _result("ok", text=text, extractor="plain-text", note="Text input used as-is.")
	if not isinstance(content, (bytes, bytearray)):
		return _result("error", note=f"Unsupported content type: {type(content).__name__}.")

	content = bytes(content)
	if content[:8].lstrip().startswith(PDF_MAGIC):
		return _extract_pdf_text(content)
	return _decode_text_bytes(content)


def _decode_text_bytes(content):
	"""Non-PDF bytes: decode as UTF-8, falling back to Latin-1 (both are
	deterministic single-pass decodes; Latin-1 never fails)."""
	try:
		text = content.decode("utf-8")
	except UnicodeDecodeError:
		text = content.decode("latin-1")
	if not text.strip():
		return _result("error", note="The provided file is empty.")
	return _result(
		"ok", text=text, extractor="plain-text", note="Non-PDF file decoded as text."
	)


def _extract_pdf_text(content):
	"""The PDF text layer via pypdf, else pdfminer.six, else a clear miss."""
	extracted = _try_pypdf(content)
	if extracted is None:
		extracted = _try_pdfminer(content)
	if extracted is None:
		return _result("extractor-missing", note=EXTRACTOR_MISSING_NOTE)

	extractor, text, pages = extracted
	if not (text or "").strip():
		return _result(
			"no-text-layer", pages=pages, extractor=extractor, note=NO_TEXT_LAYER_NOTE
		)
	return _result(
		"ok",
		text=text,
		pages=pages,
		extractor=extractor,
		note=f"Text layer extracted with {extractor}.",
	)


def _try_pypdf(content):
	"""(extractor, text, pages) via pypdf, or None when it is unavailable.

	A pypdf that is installed but fails on the file surfaces as an error
	result via the caller - not silently swallowed.
	"""
	try:
		from pypdf import PdfReader
	except Exception:
		# missing OR broken install (e.g. a bench whose cryptography build is
		# damaged raises non-ImportError at import time) - both degrade to the
		# next extractor / extractor-missing, never a crash
		return None
	reader = PdfReader(io.BytesIO(content))
	parts = []
	for page in reader.pages:
		parts.append(page.extract_text() or "")
	return "pypdf", "\n".join(parts), len(reader.pages)


def _try_pdfminer(content):
	"""(extractor, text, pages) via pdfminer.six, or None when unavailable."""
	try:
		from pdfminer.high_level import extract_text
	except Exception:
		return None  # missing or broken install - same degradation as pypdf
	text = extract_text(io.BytesIO(content))
	return "pdfminer", text or "", None


def _result(status, text="", pages=None, extractor=None, note=""):
	return {
		"status": status,
		"text": text if status == "ok" else "",
		"pages": pages,
		"extractor": extractor,
		"note": note,
	}
