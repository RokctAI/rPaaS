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

"""Deterministic pack parsing - the first pass at findings F-02 (full).

Reads a buyer's actual tender pack document (text layer only) and proposes
the checklist/returnable data the desk currently types by hand. Three
modules, all frappe-free and importable standalone (pack_builder pattern):

- ``text_extract``: pulls the text layer out of a pack PDF (or accepts
  plain text). No OCR - a scanned pack degrades to an explicit
  "no-text-layer" status, never a guess.
- ``pack_parse``: fixed pattern rules over the extracted text. Every
  extraction carries exactly one of two confidence tags: QUOTED (a
  verbatim pattern hit, with the source line captured) or NOT-FOUND.
  There is no fuzzy middle and no AI anywhere.
- ``pack_ingest``: maps a parse result onto the EXISTING capture surface
  (Tender Bid Returnable rows, bid field values) as a PREVIEW with
  disagreement warnings. Nothing auto-applies - the desk selects rows and
  the endpoint applies them only on an explicit apply=1.
"""
