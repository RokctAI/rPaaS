# Company Profile — Umzansi Infrastructure Group (Pty) Ltd

> **FICTIONAL COMPANY NOTICE.** Same fictional bidder as the five sample
> packs: every identifier is deliberately fake (registration
> `2015/999999/07`, CSD `MAAA0999999`, `555` phone exchange, reserved
> `.example` mail domain). A "FICTIONAL DEMO PROFILE" banner is rendered
> on every page of every artifact.

SA tender packs routinely list a marketing-style **"Company Profile"**
document among the returnables. The TenderAssist SDK (`tender/frappe`)
does not produce one — it builds the compliance/forms pack — but the
**designer studio SDK** (RokctAI/designer, the `designer-compliance`
engine that the `studio/` Frappe fragment wraps) does exactly this class
of deliverable. This directory is that engine run for real against the
fictional Umzansi profile.

## What was run

From two seed colours (`#0B6E4F`, `#E8A13D`) the engine derived a full
design system (palette roles, WCAG-checked ink/text tones, neutrals,
typography, print defaults), then rendered slot-marked SVG templates
through `designer.template.render` (real glyph-metric text fitting,
role-bound palette, empty slots dropped), audited every page with
`ComplianceEngine.audit`, and wrote vector PDFs with embedded TrueType
fonts via `designer.render.render_pdf` — no browser, no external
binaries, deterministic output.

## Files — GENERATED vs STUBBED

**GENERATED (real designer-SDK code, run unmodified):**

- `umzansi-company-profile-a4.pdf` — the 4-page A4 company profile
  (cover, divisions, compliance & registrations, track record & people).
  Vector PDF from `render_pdf`, one `Document` per page.
- `umzansi-profile-zfold-a4.pdf` — tri-fold A4 brochure edition, from
  the SDK's own shipped `examples/templates/agency/z-fold-a4.svg`
  template, rendered press-ready (3mm bleed, crop/registration marks,
  fold marks at the 100/99/98mm panels).
- `system.yaml` — the design system the engine derived from the two
  seeds (`designer.palette.derive_system`); reusable anywhere via
  `--system`.
- `cover-preview.png` — engine raster of page 1 (`render_png`).
- `audit.txt` — the engine's own compliance reports: pages score
  89.5–91.5/100 (remaining findings are the A4 preset's off-grid canvas
  and no-bleed layout); the shipped z-fold template audits 69.5/100
  against the derived system, mostly 8px-grid pedantry in the template's
  own geometry.

**STUBBED / authored for this run (labeled, since the designer repo
ships no A4 company-profile template — qualification: the *ecosystem*
does ship a company-profile template, `business_profile.md` in the
StartupOS engine's template suite; it is a compliance-gated content
document, not an A4 design. See `startup-os/` below):**

- `templates/*.svg` — the four A4 page templates, written for this run
  following the SDK's template conventions (`data-slot`, `data-token`
  role binding, `data-fit="shrink"`), on the `a4-poster` format preset.
  Chrome only — all content arrives via `TemplateData` fields at render
  time.
- `logo.svg` — deterministic monogram placeholder, same pattern as
  `examples/agency_demo.py`'s `make_logo`; a real client mark would be
  slotted in instead.
- All content facts: the same fictional Umzansi profile the five sample
  packs use (CIDB 6CE, B-BBEE Level 2 with the deliberate
  expiry-not-on-file gap, PSIRA security division, web/ICT unit, the
  uMzimkhulu/N2 project record, directors and key personnel) — company
  data would come from the composed site's doctypes in production.
- `generate_company_profile.py` — the runner. Reproduce with a checkout
  of RokctAI/designer at `/home/user/rokctai/designer` (or edit
  `DESIGNER_REPO`), `pip install -e` on it, then
  `python3 generate_company_profile.py out/`. Deterministic: same seeds
  and facts, same bytes out (font rasterization aside).

## The startup_os path — `startup-os/`

The client asked whether studio was used *with the startup_os tool*.
Studio wraps **two** engines: `designer-compliance` (this directory's
visual path) and **StartupOS** (`The-Rokct-Protocol`,
`core/utils/startup_os`), which the studio fragment drives through
`studio/frappe/src/tenant/startupos_bridge.py` for its Document Request
flow — and which *does* ship a company-profile template
(`business_profile.md`, one of 27 shipped templates). `startup-os/`
contains that engine run for real against the same fictional Umzansi
facts. The run compiles a ~30-document suite (canvases, plans,
annexures, a brand-aware investor deck `.pptx` using this directory's
`system.yaml`, a live-formula financial model `.xlsx`, and the design
briefs StartupOS exports *for* the designer engine), but only the two
tender-relevant documents are committed — the compliance-gated
`output/business_profile.md` and its `output/compliance_log.md`; the
rest of the suite is reproducible with the committed runner
(`python3 run_startupos_profile.py --protocol <protocol-checkout>`, see
`startup-os/README.md`). Note: the designer
package's `pyproject.toml` does **not** depend on `startupos` — the pip
dependency is declared at the studio-fragment level
(`studio/frappe/manifest.json`, git-pinned), so installing the designer
engine alone never pulls it in; see `startup-os/README.md`.

## Honest limits surfaced

- The studio Frappe fragment itself (`studio/frappe`) is
  composer-consumed and needs a composed bench + Frappe site to run its
  DocType/API flow (`create_design_request` → candidates → approval);
  what ran here is the underlying `designer-compliance` engine that the
  fragment calls — installed from the repo and used through its public
  API, which is the engine path the composed product exercises.
- The engine fits single-line text slots; it is not a word-processing
  layout engine. Multi-line body copy is therefore one slot per line in
  the authored templates — fine for a designed profile, but prose-heavy
  documents remain the pack builder's HTML territory.
- No ICC press profile is bundled, so the PDFs are RGB (the engine's
  `--cmyk` without a profile is explicitly an unmanaged proof); the
  brochure still carries full press geometry (bleed, marks, TrimBox).
