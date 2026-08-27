#!/usr/bin/env python3
"""Regenerate the Umzansi StartupOS document suite end-to-end.

This is the *startup_os* path to a company profile: the StartupOS engine
(The-Rokct-Protocol, ``core/utils/startup_os`` — the same engine the
designer repo's ``studio/frappe`` Document Request pipeline drives through
``startupos_bridge.py``), run against the SAME fictional Umzansi
Infrastructure Group facts as the five TenderAssist mock sample packs.

FICTIONAL COMPANY NOTICE: every identifier is deliberately fake
(registration 2015/999999/07, CSD MAAA0999999, TCS PIN 9999DEMO9999) and
the profile's deliberate gaps (B-BBEE certificate expiry not on file, no
postal address) are preserved so the engine's honest gap rendering shows.

Usage:
    pip install <protocol-checkout>/core/utils/startup_os
    python3 run_startupos_profile.py --protocol <protocol-checkout> [--out output]

Steps performed (all local, deterministic, no network, no AI):
  1. Build a scratch StartupOS workspace; sync the shipped templates from
     ``<protocol>/core/skills/.rok/startup_os/templates/``.
  2. ``startupos provision`` + ``expand`` the business instance, then fill
     the fictional answers below into questions.md (the SSOT).
  3. Write ``compliance_overrides.json`` (operator-asserted fictional
     values, honestly marked *override* — not *verified* — in every
     document's provenance) and the ``brand/`` design system from the
     designer engine's ``system.yaml`` two-seed derivation.
  4. ``startupos compile --render`` -> 30 markdown documents + branded
     investor_pitch_deck.pptx + financial_model.xlsx (live formulas).
  5. ``startupos briefs`` -> poster / pull-up banner / flyer design-brief
     JSONs (the schema the designer engine's brief pipeline consumes).
  6. Copy everything to --out, stamping a FICTIONAL banner atop each .md
     (the only post-processing; engine output is otherwise verbatim).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = "UmzansiInfrastructureGroup"

BANNER = (
    "> **FICTIONAL DEMO PROFILE.** Umzansi Infrastructure Group (Pty) Ltd is\n"
    "> the fictional bidder of the TenderAssist mock sample packs. Every\n"
    "> identifier is deliberately fake. This banner is stamped by\n"
    "> `run_startupos_profile.py` after generation; the StartupOS engine\n"
    "> output below is otherwise verbatim.\n\n"
)

OVERRIDES = {
    "_comment": (
        "FICTIONAL DEMO PROFILE - operator-asserted values for the fictional "
        "Umzansi Infrastructure Group (Pty) Ltd. Every identifier is "
        "deliberately fake (2015/999999/07, MAAA0999999, 9999DEMO9999). "
        "bee_expiry_date and postal_address are DELIBERATELY absent - they "
        "are the profile's documented gaps."
    ),
    "company_name": "UMZANSI INFRASTRUCTURE GROUP (PTY) LTD (FICTIONAL DEMO)",
    "reg_number": "2015/999999/07",
    "reg_date": "12 March 2015",
    "registered_office": "14 Umdoni Drive, Marburg Industrial, Port Shepstone, 4240",
    "tax_number": "9999999999",
    "tax_pin": "9999DEMO9999",
    "tax_compliance_status": "Compliant per fictional SARS TCS PIN 9999DEMO9999",
    "bee_level": "Level 2 Contributor (fictional SANAS certificate)",
    "bee_procurement_recognition": "125%",
    "bee_black_ownership": "51%+",
    "bee_cert_number": "SANAS-DEMO-9999",
    "bee_issue_date": "2025-06-30",
}

ANSWERS = {
    # 1. Venture Identity & Jurisdiction
    "Establishment Date": "12 March 2015",
    "Industry": (
        "Construction and infrastructure services — civil works (CIDB 6CE), "
        "security services (PSIRA-registered), environmental advisory, and a "
        "municipal web/ICT unit"
    ),
    "Vision Statement": (
        "To be the KwaZulu-Natal south coast's most dependable mid-tier "
        "public-infrastructure group, delivering civil works, security and "
        "digital services to municipal and provincial clients. "
        "(FICTIONAL DEMO PROFILE)"
    ),
    "Core Value Proposition": (
        "A multi-disciplinary contractor that lets public-sector buyers "
        "procure bridges, guarding and municipal web/ICT systems from one "
        "CIDB 6CE, PSIRA-registered entity with a verifiable KwaZulu-Natal "
        "delivery record."
    ),
    # 2. Market & Product
    "Primary Products": (
        "Civil works (bridges, roads, stormwater structures); security "
        "services (guarding, reaction, control-room operations); "
        "environmental reporting and socio-economic assessment; municipal "
        "websites, ZA-resident hosting and cloud helpdesk/call-centre "
        "deployments."
    ),
    "Customer Segments": (
        "South African public-sector buyers: local municipalities, "
        "provincial departments, water boards and municipal entities, "
        "principally in KwaZulu-Natal."
    ),
    "Growth Strategy": (
        "Competitive public tenders with qualifying gates matched per bid "
        "(CIDB, PSIRA, B-BBEE); repeat work won through completed-contract "
        "references and contactable municipal clients."
    ),
    "Key Competitors": (
        "Regional CIDB 6CE civils contractors, national guarding groups, and "
        "web agencies bidding municipal ICT tenders."
    ),
    "Unfair Advantage": (
        "Four registered divisions under one compliant entity — one bidder "
        "passes civil, security and ICT gates that single-discipline rivals "
        "must joint-venture to meet."
    ),
    # 3. Operations & People
    "Key Suppliers": (
        "Readymix and aggregates suppliers on the KZN south coast; "
        "PSIRA-graded labour providers; a Cape Town ZA-resident data centre "
        "(hosting resold with a 99.9% uptime SLA back-to-back); a "
        "South-African-hosted cloud call-centre platform vendor under a "
        "reseller/implementer agreement."
    ),
    "Personnel Count": (
        "Approximately 190 — 140 in the PSIRA security division per its "
        "PSIRA letter, plus civil works crews, the environmental unit and a "
        "four-person web/ICT unit."
    ),
    "Board Directors": (
        "Sipho Mthembu (Managing Director, authorised signatory); Naledi "
        "Dube (Director: Operations); Thabo Radebe (Director: Security "
        "Services, PSIRA Grade B)."
    ),
    "Shareholder Distribution": (
        "Sipho Mthembu 40%, Naledi Dube 35%, Thabo Radebe 25% (fictional "
        "demo split; 51%+ black ownership per the fictional SANAS "
        "certificate)."
    ),
    "Key Operational Risks": (
        "B-BBEE certificate expiry not captured on file (deliberate demo "
        "gap); two of three directors without PSIRA Grade B, limiting "
        "security bids above guard level; key-person dependency on the "
        "civil works lead; municipal payment cycles straining working "
        "capital."
    ),
    "Business Continuity Strategy": (
        "Hosting and call-centre services carry back-to-back SLAs with the "
        "ZA data centre and platform vendor; plant is hired per contract "
        "rather than owned; the bid pipeline is spread across four "
        "divisions so no single client or discipline dominates."
    ),
    # 4. Financial Projections & History (all fictional demo values)
    "Projected Year 1": (
        "R62m revenue, R4.3m net profit; complete two bridge contracts and "
        "the first municipal helpdesk deployment."
    ),
    "Projected Year 2": (
        "R71m revenue, R5.5m net profit; extend security contracts to two "
        "water boards."
    ),
    "Projected Year 3": (
        "R83m revenue, R7.1m net profit; three concurrent CIDB 6CE "
        "contracts and five hosted municipal platforms."
    ),
    "Historical Turnover 2024": "R54.2m",
    "Historical Turnover 2025": "R58.7m",
    "Historical Turnover 2026 YTD": "R31.4m (to end July 2026)",
    "Funding Requirement": (
        "None sought — the group bids from its own balance sheet; a "
        "fictional bank letter records an average balance above R1m."
    ),
    # Full-tier answers used by business_profile.md and friends
    "Head Office": (
        "14 Umdoni Drive, Marburg Industrial, Port Shepstone, 4240, "
        "KwaZulu-Natal"
    ),
    "Secondary Locations": (
        "Control room and security operations base, Port Shepstone; site "
        "establishments per contract."
    ),
    "Target Sectors": (
        "Municipal infrastructure, water-board security, provincial "
        "environmental reporting, municipal web and helpdesk systems."
    ),
    "Intellectual Property": (
        "None registered — delivery methods and the bid library are trade "
        "know-how; no patents or trademarks are claimed (fictional "
        "profile)."
    ),
    "Technical Architecture": (
        "Civil delivery to SANS/COLTO specifications with hired plant; web "
        "stack hosted in a ZA-resident Cape Town data centre; cloud "
        "call-centre platform resold under an implementer agreement."
    ),
    "Executive Team": (
        "Sipho Mthembu — Managing Director, BTech Civil Engineering "
        "(NQF 7), 18 years. Naledi Dube — Director: Operations (bid "
        "office). Thabo Radebe — Director: Security Services, PSIRA "
        "Grade B. Key personnel: Nomvula Khoza — N.Dip Civil Engineering "
        "(NQF 6), 9 years, site agent on two completed bridge contracts; "
        "Lerato Khumalo — BSc Computer Science (NQF 7), 8 years, web lead."
    ),
    "Key Person Dependencies": (
        "Sipho Mthembu is the only NQF 7 civil engineering lead; Thabo "
        "Radebe holds the security division's only PSIRA Grade B."
    ),
    "Quality Standards": (
        "CIDB 6CE contractor grading; PSIRA company registration; COIDA "
        "letter of good standing; SANS site safety files per contract "
        "(fictional certificates)."
    ),
    "Service Levels": (
        "99.9% hosting uptime SLA (back-to-back from the data centre); "
        "24/7 reaction and control-room cover; defects-liability "
        "compliance on completed civil contracts."
    ),
    "Achievements To Date": (
        "uMzimkhulu low-level bridge — R14.9m, completed 2024. N2 "
        "interchange approaches — R28.4m, completed 2023. Rural access "
        "culvert programme — R8.2m, completed 2023. Three public-facing "
        "websites delivered, one for a municipal entity. Three "
        "helpdesk/call-centre deployments on 12+ month terms with "
        "contactable references. (All fictional demo projects.)"
    ),
    "Brand Positioning": (
        "The compliant one-stop mid-tier bidder for KZN public "
        "infrastructure — FICTIONAL DEMO PROFILE."
    ),
    "Product Components": (
        "Civil works; security guarding and reaction; environmental "
        "advisory; municipal web, hosting and helpdesk services (fictional "
        "demo suite)."
    ),
    "Pricing Tiers": (
        "Per-tender pricing: measured bills of quantities (civils), "
        "per-post monthly rates (security), once-off plus monthly "
        "hosting/licence grids (web/ICT) — all demo values."
    ),
    # Level 2 (investor-ready) unlock answers — all fictional demo values
    "Problem Statement": (
        "Municipal and provincial buyers on the KZN south coast must split "
        "infrastructure, guarding and ICT work across separate compliant "
        "bidders, multiplying gate checks and contract administration; "
        "single-discipline contractors routinely fail one of the CIDB, "
        "PSIRA or B-BBEE gates."
    ),
    "Market Size TAM": (
        "R120bn — annual South African public-sector construction and "
        "facilities procurement (fictional demo figure, no source claimed)."
    ),
    "Market Size SAM": (
        "R6.2bn — KZN municipal and water-board civil, security and ICT "
        "tenders within the group's CIDB 6CE and PSIRA grades (fictional "
        "demo figure)."
    ),
    "Market Size SOM": (
        "R250m over 36 months — sustained share of tenders in the group's "
        "home districts at current win rates (fictional demo figure)."
    ),
    "Competitive Positioning": (
        "Regional 6CE civils rivals: equal grading, no security or ICT "
        "divisions. National guarding groups: broader footprint, no CIDB "
        "grading. Municipal web agencies: lower cost, no site-based "
        "delivery record or PSIRA cover."
    ),
    "Revenue Streams": (
        "Measured civil works contracts; monthly per-post security "
        "contracts; hosting and helpdesk subscriptions; environmental "
        "advisory fees."
    ),
    "Gross Margin Target": (
        "18% blended (12% civils, 22% security, 45% hosted services) — "
        "fictional demo targets."
    ),
    "Average Revenue Per Customer": (
        "R9.8m per annum across active public-sector clients (fictional "
        "demo figure)."
    ),
    "Customer Acquisition Cost": (
        "R120k average bid-office cost per won tender (fictional demo "
        "figure)."
    ),
    "Monthly Operating Costs": (
        "R4.1m — payroll, control room, plant hire retainers and bid "
        "office (fictional demo figure)."
    ),
    "Cash On Hand": (
        "Average bank balance above R1m per the fictional bank letter; "
        "R14m undrawn overdraft facility (fictional)."
    ),
}


def run_cli(root, *args):
    env = dict(os.environ, STARTUPOS_ROOT=root)
    subprocess.run(["startupos", *args], check=True, env=env)


def fill_answers(path):
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    label_re = re.compile(r"^\*   \*\*(.+?)\*\*")
    answer_re = re.compile(r"^(    \*   \*\*Answer\*\*: ).*$")
    filled, current, used = [], None, set()
    for line in lines:
        m = label_re.match(line)
        if m:
            current = m.group(1).strip()
        am = answer_re.match(line)
        if am and current in ANSWERS:
            filled.append(am.group(1) + ANSWERS[current] + "\n")
            used.add(current)
            continue
        filled.append(line)
    missing = set(ANSWERS) - used
    if missing:
        raise SystemExit(f"Labels not found in questions.md: {sorted(missing)}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(filled)


def write_brand(instance_dir):
    brand = os.path.join(instance_dir, "brand")
    os.makedirs(brand, exist_ok=True)
    shutil.copy(os.path.join(HERE, "..", "system.yaml"),
                os.path.join(brand, "system.yaml"))
    shutil.copy(os.path.join(HERE, "..", "logo.svg"),
                os.path.join(brand, "logo.svg"))
    committed_png = os.path.join(HERE, "brand", "logo.png")
    if os.path.exists(committed_png):
        shutil.copy(committed_png, os.path.join(brand, "logo.png"))
        return
    try:  # rasterize the monogram (deck embeds raster only)
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[note] Pillow not installed - deck renders without the logo "
              "(the engine coaches this).")
        return
    sc = 2
    img = Image.new("RGBA", (240 * sc, 240 * sc), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([8 * sc, 8 * sc, 232 * sc, 232 * sc], fill="#0b6e4f")
    d.rectangle([8 * sc, 196 * sc, 232 * sc, 232 * sc], fill="#e8a13d")
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120 * sc)
    bbox = d.textbbox((0, 0), "U", font=font)
    d.text((120 * sc - (bbox[2] - bbox[0]) / 2 - bbox[0], 150 * sc - bbox[3]),
           "U", font=font, fill="#f7fbf9")
    img.save(os.path.join(brand, "logo.png"))


def export_outputs(instance_dir, out_dir):
    src = os.path.join(instance_dir, "output")
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    shutil.copytree(src, out_dir)
    for root, _dirs, files in os.walk(out_dir):
        for name in files:
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(BANNER + body)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--protocol", required=True,
                    help="Path to a The-Rokct-Protocol checkout")
    ap.add_argument("--out", default=os.path.join(HERE, "output"))
    ap.add_argument("--workspace", default=None,
                    help="Keep the scratch workspace here (default: temp dir)")
    args = ap.parse_args()

    if shutil.which("startupos") is None:
        raise SystemExit(
            "startupos CLI not found. Install the engine first:\n"
            f"  pip install {os.path.join(args.protocol, 'core', 'utils', 'startup_os')}"
        )

    scratch = args.workspace or tempfile.mkdtemp(prefix="startupos-umzansi-")
    root = os.path.join(scratch, "StartupOS")
    templates_src = os.path.join(
        args.protocol, "core", "skills", ".rok", "startup_os", "templates")
    for kind in ("business", "life"):
        shutil.copytree(os.path.join(templates_src, kind),
                        os.path.join(root, "templates", kind),
                        dirs_exist_ok=True)

    run_cli(root, "provision", "--type", "business", "--name", INSTANCE,
            "--base", "Port Shepstone, KwaZulu-Natal, South Africa",
            "--jurisdiction", "ZA")
    run_cli(root, "expand", "--type", "business", "--name", INSTANCE)

    instance_dir = os.path.join(root, "instances", "business", INSTANCE)
    fill_answers(os.path.join(instance_dir, "questions.md"))

    os.makedirs(os.path.join(instance_dir, "compliance"), exist_ok=True)
    with open(os.path.join(instance_dir, "compliance",
                           "compliance_overrides.json"), "w",
              encoding="utf-8") as fh:
        json.dump(OVERRIDES, fh, indent=2)
    write_brand(instance_dir)

    run_cli(root, "compile", "--type", "business", "--name", INSTANCE,
            "--render")
    run_cli(root, "briefs", "--type", "business", "--name", INSTANCE)

    export_outputs(instance_dir, args.out)
    # Keep the SSOT and overrides beside the outputs for inspection.
    shutil.copy(os.path.join(instance_dir, "questions.md"),
                os.path.join(HERE, "questions.md"))
    print(f"Done. Outputs in {args.out}; scratch workspace in {scratch}")


if __name__ == "__main__":
    main()
