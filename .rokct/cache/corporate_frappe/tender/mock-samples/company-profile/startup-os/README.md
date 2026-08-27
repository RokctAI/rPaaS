# Umzansi via StartupOS — the studio's *other* engine, run for real

> **FICTIONAL COMPANY NOTICE.** Same fictional bidder as everything else
> in `tender/mock-samples/`: every identifier is deliberately fake
> (registration `2015/999999/07`, TCS PIN `9999DEMO9999`, `555` phone
> exchange). A FICTIONAL banner is stamped on every generated markdown
> document, the compiled company name itself carries "(FICTIONAL DEMO)",
> and the deliberate profile gaps (B-BBEE expiry not on file, no postal
> address) are preserved on purpose.

The parent directory answered "company profile" with the **designer
engine** (visual: a designed A4 PDF from authored SVG templates). This
directory answers it with the studio's **other** engine — **StartupOS**
(`RokctAI/The-Rokct-Protocol`, `core/utils/startup_os`) — which *does*
ship a company-profile template: `business_profile.md`, one of 27
templates at `core/skills/.rok/startup_os/templates/business/`. That is
the canonical *content* path to a company profile in this ecosystem.

## How studio, designer and startupos actually relate

The studio Frappe fragment (`RokctAI/designer` → `studio/frappe`) serves
**two personas on two engines** (its own `manifest.json` description):

| Persona | DocType flow | Engine | Seam file |
|---|---|---|---|
| Designer/agency | Design Request → candidates → approval | `designer-compliance` | `studio/frappe/src/tenant/engine_bridge.py` |
| Business executive | **Document Request** → document suite | `startupos` | `studio/frappe/src/tenant/startupos_bridge.py` |

**"studio didn't pip startup os?" — correct, and by design.** The
`designer-compliance` package's `pyproject.toml` declares only `Pillow`,
`numpy` and `PyYAML` (plus optional `pytesseract`); its
`[tool.setuptools.packages.find]` packages `designer*` only, so
`pip install -e` of the designer repo installs neither the `studio/`
fragment nor `startupos`. The `startupos` engine is declared one level
up, in `studio/frappe/manifest.json`, as a bench-level dependency
git-pinned to the protocol repo
(`startupos @ git+https://github.com/RokctAI/The-Rokct-Protocol@<sha>#subdirectory=core/utils/startup_os`),
and `startupos_bridge.py` imports it lazily with a coaching error naming
that exact pip command when absent. The two engines never import each
other — the composed studio product drives both, and StartupOS hands
work *to* the designer engine via design-brief JSONs (below).

The Frappe fragment itself (Document Request DocType,
`documents_pipeline.py` on the `long` queue) needs a composed bench +
site, which this environment does not have — same honest limit as the
parent README. What ran here is the **startupos engine the fragment
drives through `startupos_bridge.py`**, installed from the protocol
checkout (`pip install <protocol>/core/utils/startup_os` — stdlib-only)
and driven through its own CLI, mirroring the bridge's calls
(`provision` → `write questions` → `compile` → `briefs`).

## What was run

`run_startupos_profile.py` (committed, reproducible, no AI, no network):

1. **Workspace + shipped templates** synced from
   `core/skills/.rok/startup_os/templates/` (templates deliberately do
   not ship in the pip wheel — the bridge's `bootstrap_workspace`
   documents the same requirement).
2. **`startupos provision` + `expand`** → the 89-question `questions.md`
   SSOT; 49 questions answered with the same fictional Umzansi facts the
   five sample packs use (55% completeness, honestly reported).
3. **`compliance_overrides.json`** — the engine refuses to assert any
   regulated value (B-BBEE level, CIPC registration, tax status) without
   evidence. Real deployments drop certificate PDFs (`BEE.pdf`,
   `Tax_Pin.pdf`) in `compliance/`; a fictional company has none, so the
   fictional values are supplied through the engine's *operator-override*
   layer, which marks them **override**, not *verified*, in every
   document's provenance footer. `bee_expiry_date` and `postal_address`
   are deliberately absent — the engine turns them into a
   `compliance_log.md` expiry **WARNING** and a *Pending* field, the
   same deliberate gaps the sample packs carry.
4. **`brand/`** — the designer engine's two-seed `system.yaml` from the
   parent directory (the cross-engine handshake: StartupOS reads the
   exact YAML `designer palette` emits), the monogram logo, and
   `logo.png` (the deck embeds raster only; the engine coaches this
   about the svg).
5. **`startupos compile --render`** → `output/`: **30 documents** — 19
   markdown documents + 8 annexures (`business_profile.md` among them),
   `compliance_log.md`, plus a **brand-aware 12-slide
   `investor_pitch_deck.pptx`** (Umzansi greens/gold, logo on cover) and
   **`financial_model.xlsx` with live formulas** — both stdlib-rendered,
   deterministic.
6. **`startupos briefs`** → `output/briefs/` — poster, pull-up banner
   and flyer design-brief JSONs in the expo-brief schema the designer
   engine's brief pipeline consumes, copy taken verbatim from the
   founder answers (so the FICTIONAL banner rides along), `cta: null`
   coached for the owner.

Every document carries a Document Control block: engine version, content
hash, completeness, **Depth: Level 2 of 3 — investor-ready** (with the
exact unanswered questions that would unlock Level 3), and
document-backed evidence counts.

## What is committed here

The engine run above emits a **~30-document suite** (executive summary,
canvases, plans-on-a-page, annexures, investor deck `.pptx`, financial
model `.xlsx`, design-brief JSONs). This is a **tender sample pack**, so
only the two tender-relevant documents are committed:

- `output/business_profile.md` — the company-profile returnable
  (linked from the TWK sample's pack structure and requirements
  checklist);
- `output/compliance_log.md` — the certificate/expiry log the profile's
  provenance depends on.

Everything else is deliberately **not** committed. The full suite is
reproducible, deterministically, from the committed runner and its
embedded answers/overrides (after
`pip install <protocol-checkout>/core/utils/startup_os`):

```
python3 run_startupos_profile.py --protocol <protocol-checkout>
```

One knock-on, left as-is on purpose: `business_profile.md`'s "Strategic
Document Mappings" block links `01_executive_summary.md` and
`02_company_description.md`, which are not committed. The document is
engine output kept verbatim (its Document Control content hash would
break if edited); regenerating with the command above materialises the
linked documents beside it.

## GENERATED vs AUTHORED

**GENERATED (startupos engine v2.0.0, run unmodified):** the documents
in `output/` — the only post-processing is the FICTIONAL banner stamped
atop each `.md` by the runner, labeled as such in the banner itself.
(Only the two tender-relevant documents are committed; see above.)

**AUTHORED for this run:** `run_startupos_profile.py` (the fictional
answers and overrides — content, not engine code), `brand/logo.png`
(monogram raster). `questions.md` is the runner-produced SSOT, kept for
inspection.

## Correction to the parent README's template claim

The parent README says the A4 page templates were authored "since the
repo ships no A4 company-profile template". That claim **stands for the
designer repo** — its shipped templates remain business cards, A5 flyer,
pull-up banner, z-fold A4, corporate folder, signboards, a pen barrel
and 16:9 pitch-deck slides (`examples/templates/`), with no multi-page
A4 profile — **but needs one qualification**: the *ecosystem* does ship
a company-profile template. It is `business_profile.md` in
The-Rokct-Protocol's StartupOS skill, and it is a compliance-gated
*content* document, not an A4 *design*. The two outputs are
complementary, not substitutes: StartupOS compiles what the company can
truthfully say (and exports design briefs), the designer engine renders
branded visuals from briefs and templates. A composed studio site offers
both flows side by side.
