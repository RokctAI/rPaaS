#!/usr/bin/env python3
"""FICTIONAL company profile for Umzansi Infrastructure Group (Pty) Ltd,
generated with the RokctAI designer studio SDK (RokctAI/designer,
`designer-compliance` engine — the engine the studio Frappe fragment wraps).

Genuine SDK code executed (unmodified):
  - designer.palette.derive_system      (brand system from 2 seed colours)
  - designer.template.render            (slot-marked SVG templates + TemplateData)
  - designer.template.palette_for_system
  - designer.engine.Engine.audit        (design-system compliance score per page)
  - designer.render.render_pdf          (vector PDF writer, embedded TrueType)
  - designer.render.render_png          (preview raster)
  - shipped template examples/templates/agency/z-fold-a4.svg (tri-fold brochure)

Authored for this run (labeled STUBBED in the sample README):
  - four A4 page templates built here with the repo's slot conventions
    (data-slot / data-token / data-fit) — the repo ships no A4
    company-profile template
  - the monogram logo (same deterministic placeholder pattern as
    examples/agency_demo.py make_logo)
  - all content facts: the same FICTIONAL Umzansi profile used by the
    five TenderAssist mock sample packs. Every identifier is fake.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

DESIGNER_REPO = Path("/home/user/rokctai/designer")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "company-profile-out").resolve()
OUT.mkdir(parents=True, exist_ok=True)

from designer.engine import ComplianceEngine as Engine
from designer.formats import get_format
from designer.palette import derive_system
from designer.render import render_pdf, render_png
from designer.svg import parse_svg
from designer.template import (
    AGENCY_TYPE_SCALE,
    TemplateData,
    palette_for_system,
    render as render_template,
)
from designer.tokens import system_from_dict

# ---------------------------------------------------------------- brand
# Two FICTIONAL seed colours -> full design system (palette roles, WCAG
# ink/text, neutrals, typography, print defaults) via the engine.
SEEDS = ["#0B6E4F", "#E8A13D"]  # spruce green + construction amber
FONTS = {"typography": {"fonts": ["DejaVu Sans", "sans-serif"]}}

doc_data = derive_system(SEEDS, name="Umzansi Infrastructure Group (FICTIONAL)",
                         overrides=FONTS)
doc_system = system_from_dict(doc_data)

press_data = derive_system(
    SEEDS, name="Umzansi Infrastructure Group (FICTIONAL) — press",
    overrides={**FONTS, "typography": {"fonts": ["DejaVu Sans", "sans-serif"],
                                       "scale": list(AGENCY_TYPE_SCALE)}})
press_system = system_from_dict(press_data)

(OUT / "system.yaml").write_text(yaml.safe_dump(doc_data, sort_keys=False),
                                 encoding="utf-8")

palette = palette_for_system(doc_system)
PRIMARY, ACCENT, INK, SURFACE, ON_PRIMARY, PAPER = palette

# Deterministic monogram placeholder (agency_demo.make_logo pattern).
logo_svg = OUT / "logo.svg"
logo_svg.write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240" '
    'width="240" height="240">\n'
    f'  <rect x="8" y="8" width="224" height="224" fill="{PRIMARY}"/>\n'
    f'  <rect x="8" y="196" width="224" height="36" fill="{ACCENT}"/>\n'
    f'  <text x="120" y="150" text-anchor="middle" font-size="120" '
    f'font-weight="bold" fill="{ON_PRIMARY}" '
    'font-family="DejaVu Sans">U</text>\n'
    "</svg>\n",
    encoding="utf-8",
)
logo_png = OUT / "logo.png"
render_png(parse_svg(logo_svg), logo_png, width=480)

# --------------------------------------------------- A4 page templates
# Built programmatically with the repo's template conventions. Canvas is
# the a4-poster preset (794x1123 @96dpi CSS px, 5% safe margin, min text
# 12px). All positions sit on the system's 8px grid; sizes come from the
# system type scale so shrink-fitting steps correctly.

PAGE_W, PAGE_H = 794, 1123
M = 48                      # inside the 5% safe margin, on the 8px grid
CW = 696                    # content width, on the 8px grid


class Page:
    """Collects template shapes + the TemplateData fields that fill them."""

    def __init__(self, name: str):
        self.name = name
        self.parts: list[str] = []
        self.fields: dict[str, str] = {}
        self._n = 0

    def rect(self, x, y, w, h, token):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="#000000" data-token="advertiser-{token}"/>')  # compliance-ignore: auth-hardcoded-token (SVG data-token attribute in demo-data generator, not a credential)

    def text(self, value, x, y, size, token, bold=False, fitw=None,
             fith=None, anchor=None):
        self._n += 1
        slot = f"{self.name}-t{self._n}"
        self.fields[slot] = value
        attrs = [f'data-slot="{slot}"', f'x="{x}"', f'y="{y}"',
                 f'font-size="{size}"', 'fill="#000000"',
                 f'data-token="advertiser-{token}"',  # compliance-ignore: auth-hardcoded-token (SVG data-token attribute in demo-data generator, not a credential)
                 'font-family="DejaVu Sans"']
        if bold:
            attrs.append('font-weight="bold"')
        if anchor:
            attrs.append(f'text-anchor="{anchor}"')
        if fitw:
            attrs += ['data-fit="shrink"', f'data-fit-width="{fitw}"']
            if fith:
                attrs.append(f'data-fit-height="{fith}"')
        self.parts.append(f'<text {" ".join(attrs)}>x</text>')

    def image(self, slot, x, y, w, h):
        self.parts.append(
            f'<image data-slot="{slot}" x="{x}" y="{y}" width="{w}" '
            f'height="{h}" href=""/>')

    def lines(self, rows, x, y, size, token, step=None, bold=False,
              fitw=None):
        step = step or (size + size // 2)
        # keep line pitch on the 8px grid
        step = int(round(step / 8.0)) * 8
        for row in rows:
            self.text(row, x, y, size, token, bold=bold, fitw=fitw)
            y += step
        return y

    def write(self, path: Path):
        body = "\n  ".join(self.parts)
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {PAGE_W} {PAGE_H}" width="{PAGE_W}" '
            f'height="{PAGE_H}">\n  {body}\n</svg>\n', encoding="utf-8")
        return path


FICTION = ("FICTIONAL DEMO PROFILE — every identifier on this page is "
           "deliberately fake")

# ---- page 1: cover ----------------------------------------------------
p1 = Page("cover")
p1.rect(0, 0, PAGE_W, PAGE_H, 6)                 # paper
p1.rect(0, 0, PAGE_W, 320, 1)                    # primary band
p1.image("logo", M, 48, 96, 96)
p1.text("COMPANY PROFILE", M, 200, 48, 5, bold=True, fitw=CW)
p1.text("Umzansi Infrastructure Group (Pty) Ltd", M, 248, 32, 5,
        bold=True, fitw=CW, fith=40)
p1.text("Reg No 2015/999999/07 · VAT 4999999999 · CSD MAAA0999999",
        M, 288, 14, 5, fitw=CW)
p1.rect(M, 344, 240, 8, 2)                       # accent rule
p1.rect(M, 376, CW, 48, 2)                       # fictional banner
p1.text(FICTION, M + 16, 408, 16, 3, bold=True, fitw=CW - 32)
p1.text("Civil works · Security services · Environmental advisory · Web & ICT",
        M, 480, 20, 3, bold=True, fitw=CW)
y = p1.lines([
    "Umzansi Infrastructure Group is a fictional multi-disciplinary",
    "contractor headquartered in Port Shepstone, KwaZulu-Natal, built as",
    "the demonstration bidder for the TenderAssist SDK mock sample packs.",
], M, 528, 14, 3)
y = p1.lines([
    "CIDB grading:  6CE (General Building / Civil Engineering)",
    "B-BBEE status:  Level 2 (certificate expiry NOT on file — deliberate gap)",
    "Enterprise type:  Generic (over R50m — SANAS certificate)",
    "SARS TCS PIN:  9999DEMO9999",
], M, y + 24, 14, 3, bold=True)
p1.rect(M, 856, CW, 8, 2)
p1.text("Bid enquiries", M, 904, 16, 1, bold=True)
p1.lines([
    "Naledi Dube (Director: Operations)  ·  039 555 0184  ·  bids@umzansi-demo.example",
    "14 Umdoni Drive, Marburg Industrial, Port Shepstone, 4240, KwaZulu-Natal",
    "Postal address: none on file (deliberate profile gap)",
], M, 936, 14, 3, fitw=CW)
p1.text("Generated with the RokctAI designer studio SDK — deterministic "
        "template render, no AI imagery.", M, 1056, 12, 3, fitw=CW)

# ---- page 2: who we are / divisions -----------------------------------
p2 = Page("divisions")
p2.rect(0, 0, PAGE_W, PAGE_H, 6)
p2.rect(0, 0, PAGE_W, 96, 1)
p2.text("Who we are — four divisions", M, 64, 32, 5, bold=True, fitw=CW)
p2.rect(M, 128, CW, 40, 2)
p2.text(FICTION, M + 16, 152, 14, 3, bold=True, fitw=CW - 32)

y = 224
p2.text("Civil Works (CIDB 6CE)", M, y, 20, 1, bold=True); y += 32
y = p2.lines([
    "Bridges, roads and stormwater structures across KwaZulu-Natal.",
    "Led by Sipho Mthembu, BTech Civil Engineering (NQF 7), 18 years.",
    "Site agent: Nomvula Khoza, N.Dip Civil Engineering (NQF 6), 9 years,",
    "site agent on two completed bridge contracts.",
], M, y, 14, 3) + 24
p2.text("Security Services (PSIRA-registered)", M, y, 20, 1, bold=True); y += 32
y = p2.lines([
    "Guarding, reaction and control-room operations; 140 employees per",
    "the division's PSIRA letter. Director Thabo Radebe holds PSIRA",
    "Grade B; armed-response and electronic-security capability is",
    "partial (a known gap the VCW sample's gate analysis surfaces).",
], M, y, 14, 3) + 24
p2.text("Environmental & Advisory", M, y, 20, 1, bold=True); y += 32
y = p2.lines([
    "A small unit for environmental reporting and socio-economic",
    "assessment work supporting the group's public-sector bids.",
], M, y, 14, 3) + 24
p2.text("Web & ICT Unit", M, y, 20, 1, bold=True); y += 32
y = p2.lines([
    "Web lead Lerato Khumalo, BSc Computer Science (NQF 7), 8 years;",
    "one full-stack developer, one VoIP engineer, one support technician.",
    "Three delivered public-facing websites (one for a municipal entity);",
    "hosting resold on a Cape Town ZA-resident data centre, 99.9% uptime",
    "SLA back-to-back from the host; reseller/implementer agreement on a",
    "South-African-hosted cloud call-centre and ticketing platform.",
], M, y, 14, 3)
p2.text("Page 2 of 4 · FICTIONAL", M, 1056, 12, 3)

# ---- page 3: compliance & registrations -------------------------------
p3 = Page("compliance")
p3.rect(0, 0, PAGE_W, PAGE_H, 6)
p3.rect(0, 0, PAGE_W, 96, 1)
p3.text("Compliance & registrations", M, 64, 32, 5, bold=True, fitw=CW)
p3.rect(M, 128, CW, 40, 2)
p3.text(FICTION, M + 16, 152, 14, 3, bold=True, fitw=CW - 32)

y = 224
rowpairs = [
    ("Company registration (CIPC)", "2015/999999/07"),
    ("VAT registration", "4999999999"),
    ("CSD supplier number", "MAAA0999999 (bank details current on CSD)"),
    ("SARS tax compliance PIN", "9999DEMO9999"),
    ("CIDB contractor grading", "6CE — General Building / Civil Engineering"),
    ("B-BBEE status level", "Level 2 (SANAS) — certificate expiry NOT on file"),
    ("PSIRA (security division)", "Company registration valid; 1 of 3 directors Grade B"),
    ("COIDA", "Letter of good standing (fictional certificate)"),
    ("Banking", "Average balance above R1m (fictional bank letter)"),
]
for label, value in rowpairs:
    p3.text(label, M, y, 14, 1, bold=True)
    p3.text(value, M + 264, y, 14, 3, fitw=CW - 264)
    y += 40
y += 8
p3.text("Known profile gaps (deliberate — the SDK renders them as amber blocks)",
        M, y, 16, 1, bold=True, fitw=CW); y += 32
p3.lines([
    "B-BBEE certificate expiry date not captured on the business profile.",
    "No postal address on file.",
    "Director Thabo Radebe's tax reference number missing.",
    "Two directors without PSIRA Grade B (security bids above guard level).",
], M, y, 14, 3)
p3.text("Page 3 of 4 · FICTIONAL", M, 1056, 12, 3)

# ---- page 4: track record & people ------------------------------------
p4 = Page("track")
p4.rect(0, 0, PAGE_W, PAGE_H, 6)
p4.rect(0, 0, PAGE_W, 96, 1)
p4.text("Track record & people", M, 64, 32, 5, bold=True, fitw=CW)
p4.rect(M, 128, CW, 40, 2)
p4.text(FICTION, M + 16, 152, 14, 3, bold=True, fitw=CW - 32)

y = 224
p4.text("Selected completed projects (fictional)", M, y, 20, 1, bold=True)
y += 32
y = p4.lines([
    "uMzimkhulu low-level bridge — R14.9m, completed 2024.",
    "N2 interchange approaches — R28.4m, completed 2023.",
    "Rural access culvert programme — R8.2m, completed 2023.",
    "Three public-facing websites incl. one municipal entity (web unit).",
    "Three helpdesk/call-centre deployments, one municipal, on 12+ month",
    "terms with contactable references (web/ICT unit).",
], M, y, 14, 3) + 24
p4.text("Directors", M, y, 20, 1, bold=True); y += 32
y = p4.lines([
    "Sipho Mthembu — Managing Director (authorised signatory).",
    "Naledi Dube — Director: Operations.",
    "Thabo Radebe — Director: Security Services (PSIRA Grade B).",
], M, y, 14, 3) + 24
p4.text("Key personnel", M, y, 20, 1, bold=True); y += 32
y = p4.lines([
    "Sipho Mthembu — BTech Civil Engineering (NQF 7), 18 years.",
    "Nomvula Khoza — N.Dip Civil Engineering (NQF 6), 9 years, site agent.",
    "Lerato Khumalo — BSc Computer Science (NQF 7), 8 years, web lead.",
], M, y, 14, 3) + 24
p4.rect(M, y, CW, 8, 2); y += 40
p4.lines([
    "This document is a demonstration artifact of the RokctAI studio SDK.",
    "The bidder, its people, projects, registrations and every number are",
    "FICTIONAL, created for the TenderAssist mock sample packs.",
], M, y, 14, 3, bold=True)
p4.text("Page 4 of 4 · FICTIONAL", M, 1056, 12, 3)

# ------------------------------------------------------------- render
a4 = get_format("a4-poster")
engine = Engine(doc_system, format=a4)
tpl_dir = OUT / "templates"
tpl_dir.mkdir(exist_ok=True)
pages_dir = OUT / "pages"
pages_dir.mkdir(exist_ok=True)

docs = []
audit_lines = []
for page in (p1, p2, p3, p4):
    tpl_path = page.write(tpl_dir / f"{page.name}.svg")
    data = TemplateData(fields=page.fields, palette=palette,
                        images={"logo": str(logo_png)})
    doc = render_template(parse_svg(tpl_path), data, doc_system)
    report = engine.audit(doc)
    audit_lines.append(f"== page {page.name}: score {report.score}/100")
    audit_lines.append(report.to_text())
    from designer.svg import save as save_svg
    save_svg(doc, pages_dir / f"{page.name}.svg")
    docs.append(doc)

profile_pdf = OUT / "umzansi-company-profile-a4.pdf"
render_pdf(docs, profile_pdf, format=a4)
render_png(docs[0], OUT / "cover-preview.png", width=700)

# ------------------------------------------- z-fold brochure (shipped)
zfold_tpl = parse_svg(DESIGNER_REPO / "examples/templates/agency/z-fold-a4.svg")
zfold_fields = {
    "business-name": "Umzansi Infrastructure Group (Pty) Ltd",
    "tagline": "Civil works · Security · Environmental · Web & ICT",
    "phone": "039 555 0184 · Naledi Dube",
    "email": "bids@umzansi-demo.example",
    "address": "14 Umdoni Drive, Marburg Industrial, Port Shepstone 4240 — FICTIONAL DEMO PROFILE",
}
zfold_doc = render_template(
    zfold_tpl,
    TemplateData(fields=zfold_fields, palette=palette_for_system(press_system),
                 images={"logo": str(logo_png)}),
    press_system)
zspec = get_format("z-fold-a4")
zreport = Engine(press_system, format=zspec).audit(zfold_doc)
audit_lines.append(f"== z-fold brochure: score {zreport.score}/100")
audit_lines.append(zreport.to_text())
zfold_pdf = OUT / "umzansi-profile-zfold-a4.pdf"
render_pdf(zfold_doc, zfold_pdf, format=zspec, bleed=press_system.bleed,
           marks=True)

(OUT / "audit.txt").write_text("\n".join(audit_lines), encoding="utf-8")
print("\n".join(l for l in audit_lines if l.startswith("==")))
print("wrote:", profile_pdf, zfold_pdf)
