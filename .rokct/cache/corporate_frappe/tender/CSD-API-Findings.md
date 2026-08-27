# Does South Africa's CSD (Central Supplier Database) have an API?

Research date: 2026-08-18. Question: can TenderAssist (a bidder/supplier-side system) pull CSD data programmatically?

## Bottom line

**Yes, the CSD has machine interfaces — but they are exclusively for organs of state (OoS), not suppliers.** National Treasury provides (1) real-time web services and (2) bulk data files to OoS "system accounts" that are provisioned via a CFO-approved paper application form emailed to business.support@csd.gov.za and approved by the OCPO — there is no public developer portal, no self-service API keys, no published WSDL/Swagger, and no supplier-facing API. Suppliers interact with their own data only through the secure.csd.gov.za web login (and its reports). An `api.csd.gov.za` host exists and serves an ASP.NET app, but it is undocumented and returns errors to unauthenticated requests.

---

## 1. VERIFIED: OoS web services + bulk data exist (official Treasury document, text extracted directly)

Source: National Treasury / OCPO, "Central Supplier Database — User Acceptance Testing / Search Functionality Training" (CSD Team), hosted at
`https://ocpo.treasury.gov.za/buyers_area/Supplier-Management/search%20tool.pdf` — PDF fetched and text extracted 2026-08-18.

Page 16, "Consumer access to information" (verbatim):

> 1) Online search functionality via CSD application based on supplier Commodity and Location.
> 2) Real time: **web services that are made available to OoS to consume supplier information from the CSD.** Call and request latest update on supplier when needed.
> 3) Bulk data: **files that are made available to OoS to consume supplier information from the CSD in bulk format.**

Page 17 describes the consumption pipeline: CSD → Staging Area → OoS Demand/SCM/FIN systems ("Extract, Transform, Load", "Bulk / Daily / Monthly", "Real time verification of bank and tax additions/changes").

Page 18, "System Account to access CSD services" — the provisioning process (verbatim flow):

> Request OoS System Account application form: **business.support@csd.gov.za** → CSD support returns the system account application form to the requestor → **OoS completes form and obtains CFO approval. Submit application** → **OCPO office confirms and approves the identity of the requestor** → CSD support creates the system account → OoS access CSD services.

So: access is gated on being a recognised organ of state, with CFO sign-off and OCPO identity approval. No technical spec (SOAP vs REST, WSDL) is published in this document; the same email-based, form-based process also governs the human "search functionality" primary-user accounts (page 21).

Corroboration (VERIFIED, quoted from fetched page): CSD Terms and Conditions, `https://secure.csd.gov.za/Home/Terms`:

> "automated verification means electronic verification of the key information of the supplier through interfaces between the Central Supplier Database system and the systems of interfacing institutions"
> "A supplier who has submitted the requisite supplier information on the CSD hereby authorises the National Treasury to disseminate, **on request by an organ of state**, the key information"
> "validity timeframe means a twenty-four-hour period for which key information is deemed to be valid"
> The National Treasury "may ... deny, suspend or terminate the access" of a user, supplier or organ of state.

Note the Terms' "interfacing institutions" (SARS, CIPC, DHA, banks) are the *upstream* verification sources feeding the CSD — a separate integration layer from the *downstream* OoS-consumption web services.

Scale corroboration (VERIFIED, text extracted from fetched PDF): 2018 CSD Fact Sheet submitted to the UN Public Service Awards (`https://publicadministration.un.org/unpsa/.../2018 CSD Fact Sheet.pdf`) reports **"102 Back-Office Systems commenced with CSD integration"** and **"34 Back-Office systems regularly access CSD"** — i.e., government financial/SCM back-office systems are the actual consumers of the integration services. The same fact sheet: "CSD electronically verifies and on a daily basis re-verifies ... Tax clearance verification of suppliers with SARS; Business registration and business directorship verification ... with CIPC; Inclusion in the register for Tender Defaulters and Database of Restricted Suppliers; Government employee verification ... real-time check; South African ID Numbers ... checked against Home Affairs."

## 2. VERIFIED: probing for public endpoints (curl, 2026-08-18)

- `https://api.csd.gov.za/` — **exists** (resolves through Treasury reverse proxy `ntsecrevpx.treasury.gov.za`, Microsoft-IIS/10.0, ASP.NET) but returns **HTTP 500 "Runtime Error"** at root and at `/help`; `/swagger`, `/wsdl`, `/odata`, `/*.svc`, `/api/supplier` all 404. Undocumented, no discoverable contract — consistent with a private, credentialed service surface, not a public API.
- `https://secure.csd.gov.za/api` — 500 (route exists, errors); `/swagger`, `/Services`, `/webservices` — 404.
- No public WSDL or Swagger/OpenAPI document found anywhere (site probes + web searches).

## 3. Supplier/private-party access: login-only

- **No supplier-facing API.** All official material (CSD site, OCPO user guides, fact sheets) routes suppliers exclusively through the secure.csd.gov.za web application: self-register, get the **MAAA supplier number** ("supplier number and unique registration reference number ... auto-generated and communicated" — search tool.pdf p.5), maintain data, and pull reports via **Reports → Supplier Registration Summary → Download PDF** (search-result claim, consistent with the guides; report includes identification, commodities, bank, **tax compliance status**, ownership/B-BBEE fields).
- The official self-service report (the "CSD Report" PDF) is the supplier's only machine-obtainable artifact, and only via browser session — no documented public verification URL for third parties to check a report without a CSD/OoS login.
- **eTenders angle** (corroborates internal integration, confirmed earlier in this project and by the eTenders e-Submission User Manual, `https://www.etenders.gov.za/.../e-Submission_User Manual For Suppliers.pdf`, search-verified): suppliers log in to etenders.gov.za **with their CSD email address and CSD password** — i.e., eTenders authenticates against CSD as a government-side integration. This proves state systems consume CSD auth/data server-to-server; it does not open anything to private parties.
- **Third-party SCM systems** (search-result claims, not independently verified): BCX SOLAR municipal suite advertises "Supplier Database Management integrated with Treasury's CSD" (`https://www.bcx.co.za/industries/government-sector/solar-municipal-solutions/`); Treasury's mSCOA/IFMS panel vendors (Munsoft, Sebata, SAP-based) integrate similarly — all acting *on behalf of a municipality/OoS* under the OoS system-account regime, which is exactly what the "Back-Office Systems" counts in the 2018 fact sheet measure.

## 4. Circulars / instruction notes

- **NT Circular 3 of 2015/2016** (quoted inside the verified search-tool PDF): mandated migration of institutional supplier databases to CSD; from CSD registration, bidders need not submit hard-copy proof of key information.
- **NT SCM Instruction Note 4A of 2016/17 "Central Supplier Database"** (`http://ocpo.treasury.gov.za/Resource_Centre/Legislation/Instruction no 4A of 1617 Central Supplier Database.pdf`) — **dead/unavailable at research time (HTTP 503)**; by title it mandates OoS use of the CSD for verification. Not quoted here since it could not be fetched.
- OCPO CSD document library: `https://ocpo.treasury.gov.za/Suppliers_Area/Central Supplier Database/CSD User Guide Master.pdf` and `.../buyers_area/Supplier-Management/` (user guides, support-tool guide) — none publish an API spec.

## 5. Practical implications for TenderAssist (bidder-side)

Since there is no supplier/private API:

1. **Treat the MAAA number as the canonical key.** Store it per client; it is what every OoS uses to look the supplier up, and what SBD forms ask for.
2. **Store and parse the CSD Registration Summary Report PDF.** Have the client download it from Reports → Supplier Registration Summary (or capture it via a user-driven, credentialed browser session with the client's consent) and extract: MAAA number, unique registration reference, tax compliance status, bank verification status, B-BBEE, commodities, expiry/verification dates.
3. **Track freshness.** The Terms define a 24-hour validity window for key information, and CSD re-verifies SARS/CIPC daily — so flag any stored report older than the tender's needs (many buyers want a report generated within the last ~30 days, and tax status can flip). Prompt re-download before each submission.
4. **Do not attempt to consume the OoS web services** — they require a CFO-approved OoS system account; a private SaaS does not qualify. If ever needed, the only legitimate path would be partnering with/acting as a processor for an organ of state, or asking National Treasury (business.support@csd.gov.za) directly — expect "no" for supplier-side use.
5. eTenders' CSD-credential login means a client's CSD password also unlocks eTenders; handle those credentials (if ever handled at all) with corresponding care.

## Source list

Verified by fetch/extraction:
- https://ocpo.treasury.gov.za/buyers_area/Supplier-Management/search%20tool.pdf (web services / bulk data / system-account process — pp. 5, 16–18, 21)
- https://secure.csd.gov.za/Home/Terms (definitions, dissemination to OoS, 24h validity, access termination)
- 2018 CSD Fact Sheet, publicadministration.un.org UNPSA submission (back-office integration counts, daily re-verification)
- curl probes of https://api.csd.gov.za/ and https://secure.csd.gov.za/ paths (undocumented ASP.NET host, no swagger/WSDL)
- https://www.treasury.gov.za/comm_media/press/2020/CSD%20Search%20-%20Organ%20of%20State%20Practitioner%20V1.1.pdf (OoS search UI one-pager; no API content)

Search-result claims (not independently fetched):
- https://tenderprosa.co.za/compliance/csd-report (report download steps; fetched — confirms no public verification URL described)
- https://www.bcx.co.za/industries/government-sector/solar-municipal-solutions/ (SOLAR–CSD integration)
- https://www.etenders.gov.za/ e-Submission User Manual (CSD-credential login)
- https://www.sita.co.za/content/central-supplier-database

Dead/unavailable at research time:
- http://ocpo.treasury.gov.za/Resource_Centre/Legislation/Instruction%20no%204A%20of%201617%20Central%20Supplier%20Database.pdf (HTTP 503)
