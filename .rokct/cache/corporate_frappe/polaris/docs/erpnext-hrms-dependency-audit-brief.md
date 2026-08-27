# Task Brief: Audit Remaining ERPNext/HRMS Dependency in Polaris Lending

> Self-contained brief for a fresh session. Read in full; should not require the conversation that
> produced it. All 7 phases of the Lending-app fork are done (see git log: `0bbc00a` through `cbbb556` in
> `corporate`, `0280acf` in `RokctAI_frontend`, all committed locally, not pushed). The backend Python
> layer was verified to have zero `lending.`/`erpnext.` imports. This brief is a follow-up audit — the
> user recalls Polaris using HRMS for assets and possibly ERPNext more broadly, and wants that checked
> properly before considering the dependency question closed.

## What's already confirmed (don't re-derive)

- Zero `from lending.` / `from erpnext.` Python imports anywhere in `corporate/polaris/frappe` (grepped
  directly).
- `corporate/polaris/frappe/manifest.json` has no `required_apps` declaring `lending`/`erpnext`.
- **One already-disclosed, still-open ERPNext coupling**: `RokctAI_frontend/app/services/all/lending/loan.ts`'s
  `getAssetAccounts()` queries ERPNext's `Account` doctype (`root_type: "Asset"`) to feed
  `realisePawnAsset()`/Loan Write Off's `asset_account` param — flagged by the lending session itself as a
  known gap tied to the pledged-collateral/security-shortfall subsystem Phase 5 deliberately left unbuilt
  (no evidence of what "secured" means in Polaris's actual single-pawned-asset model).
- No HRMS references found in `corporate/polaris/frappe` or `RokctAI_frontend`'s lending
  services/actions/pages (grepped directly, case-insensitive) — but this doesn't rule out HRMS dependency
  existing somewhere outside what's already been forked/traced.

## What to actually check

1. **Full doctype-name-reference audit, not just import statements** — the established coupling pattern
   in this codebase is doctype-name-only generic RPC (`frappe.get_doc("Asset", ...)`,
   `frappe.get_all("Employee", ...)`, etc.) with zero Python import required. Grep the *entire* Polaris
   scope (backend `corporate/polaris/frappe`, both frontend copies `RokctAI_frontend` and
   `corporate/polaris/nextjs`) for references to known ERPNext doctypes (`Account`, `Asset`, `Item`,
   `Company`, `Sales Invoice`, `Journal Entry`, `GL Entry`, `Cost Center`, etc.) and known HRMS doctypes
   (`Employee`, `Salary Slip`, `Loan` — note HRMS has its own unrelated `Loan` concept for staff loans,
   don't confuse it with Polaris's customer-lending `Loan` — `Leave Application`, `HR Settings`, etc.).
   Don't assume a short list is exhaustive; check what doctypes ERPNext/HRMS actually define
   (`Frappenize/lending`'s sibling apps if available locally, or your knowledge of standard ERPNext/HRMS
   doctype names) against what actually gets referenced.
2. **Audit "the original," not just what's been forked** — the fork only covers what `rlending` and
   `RokctAI_frontend`'s lending module already touch. If the *actual production/original* Polaris
   implementation (wherever that lives — check if there's a deployed version, a different branch, or
   documentation describing it beyond what's in this local checkout) references ERPNext/HRMS doctypes that
   never made it into what got forked, that's a real gap the fork hasn't addressed at all, not just an
   open item within it. Determine what "the original" means concretely (a live Frappe site's installed
   apps list, a deployment config, `apps.txt` somewhere) before concluding there's nothing more to find —
   don't just re-scan the same files already checked and call it done. **Do not reference or cite
   `RokctApp/lib_backup`** under any circumstances — it's off-limits per standing project rule (it's a
   backup of a non-SDK app, not evidence for architecture decisions).
3. **Resolve or fully scope the known `getAssetAccounts()` gap.** Determine concretely: does removing the
   ERPNext dependency here require building real asset/collateral-account logic (a real gap to scope,
   possibly its own follow-up brief), or is this call genuinely dead code no live flow reaches (check
   real callers of `realisePawnAsset()`/Loan Write Off's asset-realization path)? Don't guess — trace it.
4. **Check `asset_realisation.py`** (`corporate/polaris/frappe/src/rlending/asset_realisation.py` —
   referenced in earlier git status as a modified file during this fork) specifically, since its name
   strongly suggests it's the backend counterpart to the frontend's asset-account gap.

## What NOT to do

- Don't assume "zero Python imports" means "zero dependency" — that's exactly the gap this brief exists to
  close. Doctype-name references count as real coupling.
- Don't conflate HRMS's own unrelated `Loan` doctype (staff loans) with Polaris's customer-lending `Loan`
  — already confirmed unrelated in an earlier investigation, don't re-litigate that, just don't let it
  cause a false-positive in this audit.
- Don't fabricate a resolution for the `getAssetAccounts()` gap in this pass unless it turns out to be
  genuinely dead/unreachable code — if real logic is needed, scope it as a follow-up, don't invent LTV/
  collateral math with no evidence behind it (same restraint already correctly applied in Phase 5).

## Deliverable

A clear, evidenced answer to: does Polaris (backend + both frontend copies) still depend on ERPNext and/or
HRMS anywhere, via import or doctype-name reference? A concrete resolution or scoped follow-up for the
`getAssetAccounts()`/`asset_realisation.py` gap specifically. And an honest statement of what "the
original" actually refers to and whether it was checked, not just what's in this fork. Report back with
evidence — file:line citations, not a "should be fine" summary.
