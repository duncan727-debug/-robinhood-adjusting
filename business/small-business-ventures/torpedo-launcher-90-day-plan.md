# Torpedo launcher — 90-day plan + patent findings + design brief

**For:** Duncan + son
**Drafted:** 2026-05-23 15:20 EDT
**Status:** Patent search Phase 1 complete. Design brief drafted. CAD tooling recommended. Son-ready prototype task defined.

> **Honest scope note up front:** I (Smith) can do real patent research, write design briefs, and produce SVG sketches the son can CAD from. I **cannot** run Fusion 360 or 3D-print. CAD modeling is a hands-on task that has to happen on your workstation. Where this doc says "we" build a model, it means "the son builds it from this brief." Where it says "I" or "Smith" did something, it means I actually did it in this session.

---

## Patent findings — Phase 1 (verified this session)

### 🟢 GREEN — the core torpedo design is in the public domain

**US 6,699,091 B1 — "Hand-launchable underwater projectile toy"**
- Inventor: Jon A. Warner (the original Toypedo inventor)
- Filed: November 4, 1999
- **Status: EXPIRED** (lifetime, anticipated expiration November 4, 2019)
- Source: [Google Patents — US6699091B1](https://patents.google.com/patent/US6699091B1/en)

**What this means for us:** The hand-launchable underwater torpedo design itself — neutrally-buoyant hydrodynamic body, fin-stabilized tail, specific-gravity 0.7-1.3 range — is **no longer protected**. We can manufacture and sell our own proprietary torpedo without licensing from SwimWays / Spin Master.

This is the most important single finding in this memo. It collapses the largest risk in the razor-blade business model.

### 🟡 YELLOW — launcher mechanism patent landscape needs deeper review

Searches surfaced launcher-relevant prior art including:
- US 20150176940 A1 — Toy Projectile Launcher with Spring Loaded Spools ([Google Patents](https://patents.google.com/patent/US20150176940A1/en))
- US 3,890,919 — External launcher for underwater weapon (1975, military)
- US 5,448,941 — Underwater delivery system (1995)
- US 4,185,345 — Neg'ator spring-powered underwater launching device
- US 9,127,900 — Launcher device for launching a series of items into a spin

**What I could NOT verify in this session:**
- Whether the Toypedo Blast launcher (the actual SwimWays product) has its own active patent. The SwimWays patent portal (`patents.swimways.com`) returned a TLS certificate error; the Justia SwimWays assignee page returned 403. **Conclusion: an attorney patent search is required before any tooling spend.** Budget $500-1,500 for a focused freedom-to-operate (FTO) search by a registered patent attorney. This is non-negotiable.
- I did NOT find a patent specifically claiming "underwater-only firing interlock for toys." Military/ordnance underwater interlocks exist but are different art. This is a positive signal — but does not constitute clearance.

### 🔴 RED — known proprietary marks to avoid

- **TOYPEDO®** is a registered trademark of SwimWays / Spin Master. Do not use any variant ("toypedo," "torpedo-pedo," etc.) in our branding.
- SwimWays "Toypedo Bandits" — proprietary product name, avoid.

### Patent strategy recommendation

1. **Day 1-7 (free, DIY):** I will run additional Google Patents + USPTO TESS searches on key terms ("underwater toy launcher," "water-actuated safety interlock toy," "pool toy projectile launcher") and write up findings. This is Phase 2 of the search.
2. **Day 14-28 (paid, attorney):** Engage a patent attorney for a focused FTO search. Estimated cost $500-1,500. Required output: a written FTO opinion identifying any in-force patent claims our design might infringe.
3. **Day 30-45 (if FTO clean):** File provisional patent on our specific mechanism + safety interlock. DIY USPTO microentity filing ~$300, or $1,200 with attorney drafting. A provisional gives 12 months of "patent pending" status.
4. **Day 45-90:** Continue product development under patent-pending status; convert to non-provisional within 12 months if commercially validated.

---

## Design brief — "Braun / Apple of pool toys"

Direction from Duncan, 2026-05-23 15:14 EDT: *"It should look nothing like the SwimWays Toypedo Blast. That looks cheap like a 2000-year Windows computer. We want our product to feel like a Mac / Braun design."*

### Design principles (Dieter Rams + Apple industrial design)

| Principle (Rams) | Translation to this product |
|---|---|
| Good design is innovative | Our launcher should look like nothing else in the pool aisle — different silhouette, different materials feel |
| Good design makes a product useful | Every visible feature has a function. No decorative trim, no fake vents, no plastic chrome accents |
| Good design is aesthetic | Honest material, careful proportions, considered color palette |
| Good design makes a product understandable | A child should grasp the load/aim/fire loop in <10 seconds with no instructions |
| Good design is unobtrusive | When not in use, it should look like a designed object on a poolside shelf — not a toy demanding attention |
| Good design is honest | If it's plastic, it should look like *good* plastic — not "metallic-effect" sticker chrome |
| Good design is long-lasting | Pool chlorine + UV resistance built into material choice; no stickers/decals that peel |
| Good design is thorough down to the last detail | Trigger feel, loading click, indicator color, weight balance — all considered |
| Good design is environmentally friendly | Single-material body where possible (recyclable); replaceable spring (not throwaway) |
| Good design is as little design as possible | One color body + one accent color. No graphics. Brand mark debossed/etched, not printed. |

### Specific aesthetic moves

- **Form:** elongated barrel + ergonomic grip, not "gun-shaped." Think pool-skimmer-handle-meets-power-drill, not Nerf blaster. A cleaner version of a flashlight silhouette.
- **Material:** matte-finish ABS or PC (polycarbonate) body in a single hero color. Glass-bead-blasted texture suggests premium injection-molding, costs almost no more than glossy.
- **Color palette (one of three):**
  1. **Off-white body + single bright accent** (Apple/Braun classic) — pale beige or warm white body, single safety-orange or signal-yellow trigger/loading-indicator
  2. **Charcoal body + cream accent** (sophisticated, less kid-coded — broader market)
  3. **Sea-foam or pool-blue body + white accent** (pool-context aware, summer)
- **Avoid:** primary-color rainbow blocks, fake chrome, racing stripes, character branding, transparent neon plastic, any visual "extreme sports" cliché.
- **Branding:** debossed wordmark on the grip, no printed logo. Sans-serif, single weight, mid-size. Brand name TBD (do not use "Torpedo" — too generic + SwimWays-adjacent).
- **Loading indicator:** a single small port that shows red (locked/empty) or green (loaded + ready). No more, no less. No LCD screens, no electronics if avoidable.
- **Trigger:** a single satisfying "click" travel of ~8-10mm. Like a good cable-release shutter button, not a Nerf gun double-action.
- **Torpedo design:** complement the launcher's clean lines. Soft TPE in the same accent color. Aerodynamic-spec fins, no graphic decoration on the body.

### What SwimWays' Toypedo Blast does wrong (and we don't repeat)

- Visible mold lines, sprue gates, and uneven seams = looks like a 2010 dollar-store knockoff
- Translucent green/orange "Nickelodeon Slime" plastic palette
- Visible foam blocks that customers have to remove via YouTube to make the thing work — design that fights its user
- Asymmetric silhouette with no clear axis — the eye can't tell where the front is
- Sticker-printed branding that peels in chlorine

---

## CAD tooling recommendation (for the son to install)

| Tool | Best for | Cost | Source |
|---|---|---|---|
| **Tinkercad** | First 1-2 days. Web-based, drag-and-drop, zero learning curve. | Free | [tinkercad.com](https://www.tinkercad.com/) |
| **Autodesk Fusion 360 Personal** | The real CAD workhorse for this project. Parametric modeling, simulation, export to STL for 3D print. Free for <$1,000 annual hobby revenue; renewable 3-year personal license. | Free (personal use) | [autodesk.com/products/fusion-360/personal](https://www.autodesk.com/products/fusion-360/personal) |
| **OnShape Free** | Browser-based alternative if Fusion install is finicky. Requires designs to be **public** in free tier — fine for prototypes, NOT for the final design. | Free (public-only) | [onshape.com](https://www.onshape.com/) |
| **FreeCAD** | Fully open-source backup if Autodesk discontinues hobby tier. Steeper learning curve. | Free | [freecad.org](https://www.freecad.org/) |

**Recommendation:** Son installs **Fusion 360 Personal** as primary. Use Tinkercad only for the very first sketch session if Fusion's UI feels intimidating on day 1.

### Tutorials I recommend (verified high-quality, publicly available)

- Autodesk's "Fusion 360 for Absolute Beginners" official series on YouTube (search "Fusion 360 for absolute beginners" — Autodesk's own channel)
- Lars Christensen's Fusion 360 tutorials (long-running channel, well-regarded)
- The official Fusion 360 quickstart at help.autodesk.com

These I am pointing to as known channels/sources; I have not watched specific videos this session. Browse and pick what suits his style.

---

## 90-day plan (week-by-week)

### Phase 1 — Validate the concept (Weeks 1-3, total spend <$200)

| Week | Owner | Task | Deliverable |
|---|---|---|---|
| 1 | Smith | Phase-2 patent search (Google Patents + USPTO TESS); document findings | Memo of additional prior art |
| 1 | Son | Install Fusion 360 Personal; complete 3-hour tutorial sequence | Workstation set up; tutorial complete |
| 1 | Father | Buy 1× SwimWays Toypedo Blast on Amazon for teardown | Physical reference in hand (~$20) |
| 2 | Son + Father | Disassemble Toypedo Blast; photograph mechanism; identify every part and its function | Annotated photo set + notes |
| 2 | Son | First CAD pass — launcher exterior form (no mechanism yet). Express the Braun/Apple aesthetic per design brief above | STL file v0.1 |
| 3 | Son | CAD mechanism v0.1 — spring-driven plunger, dry-fire interlock (mechanical, not foam) | STL file with internals |
| 3 | Son + Father | 3D-print v0.1 (PLA okay for first pass; ABS for water testing) | Printed prototype in hand |

**Gate at end of Week 3:** Does the printed prototype, hand-loaded with a soft foam dummy projectile, behave plausibly when actuated dry on the kitchen table? If yes → continue. If no → iterate mechanism, do not proceed.

### Phase 2 — Real prototype + legal foundation (Weeks 4-7, total spend $1,500-3,000)

| Week | Owner | Task |
|---|---|---|
| 4 | Father | Engage patent attorney for FTO search ($500-1,500). Required deliverable: written FTO opinion |
| 4 | Son | Iterate to v0.2 — proper torpedo design that mates only to our barrel; test glide in pool with launcher v0.1 |
| 5 | Father | Form Florida LLC via Sunbiz online ($125). Working name TBD per brand work in week 7 |
| 5 | Father | Quote product liability insurance ($1,200-2,500/yr); secure verbal hold |
| 6 | Son | Pool-test v0.2 in your home pool. Measure: max distance, reliability across 50 shots, behavior in <24" depth (vs. Toypedo Blast's 4 ft requirement) |
| 6 | Son + Father | Iterate to v0.3 based on pool data |
| 7 | Father + Smith | Brand work: name candidates (3-5), trademark search via USPTO TESS, secure .com domain (do this before public talking) |

**Gate at end of Week 7:** FTO opinion clean? v0.3 reliably works in shallow water? Brand cleared for trademark? If all three yes → continue. If any no → resolve before money spent on tooling.

### Phase 3 — Production prep (Weeks 8-12, total spend $7,000-15,000 conditional)

| Week | Owner | Task |
|---|---|---|
| 8 | Father | File provisional patent on the specific mechanism + interlock (DIY USPTO microentity $300, or $1,200 with attorney) |
| 8-9 | Son + Father | Send v0.3 STL files to 3 China injection-molders for tooling quote. Use Alibaba Verified Suppliers + ProtoLabs (US, more expensive but faster) for comparison |
| 9 | Father | Engage product safety lab for preliminary CPSC + ASTM F963 review (Intertek, SGS, or Bureau Veritas). $3,000-5,000 for full battery; do NOT skip |
| 10 | Father | Choose injection molder; sign tooling PO ($4,000-8,000 for launcher mold, $1,500-3,000 for torpedo mold) |
| 10 | Son | Kickstarter pre-launch page: video draft, story, FAQ, prototype demo footage from week 6 |
| 11 | Father + Son | T1 sample from molder reviewed and signed off. Tooling adjustments if needed |
| 12 | Both | Kickstarter goes live; first production run paid for by pre-orders (target $30-40K raised) |

**Gate at end of Week 12 (Day 90):** Kickstarter funded? Tooling on track? CPSC tests passed? If all three → production proceeds and we are in business. If any no → reassess and decide whether to push timeline or kill.

---

## Total cash exposure by phase

| Phase | Weeks | Total commit | What you have to show for it |
|---|---|---|---|
| Phase 1 | 1-3 | ~$200 | Working prototype, validated mechanism, patent context |
| Phase 2 | 4-7 | ~$1,500-3,000 | FTO clearance, LLC, insurance hold, pool-tested v0.3, brand cleared |
| Phase 3 | 8-12 | ~$7,000-15,000 | Tooling, CPSC tests, provisional patent, Kickstarter launched |
| **End of Day 90** | | **~$8,700-18,200** | First production run funded by Kickstarter pre-orders, or decision to kill the project |

The phase structure is designed so you can **stop after any phase** with limited downside:
- Stop after Phase 1: you spent $200 + son learned CAD. Net positive.
- Stop after Phase 2: you spent ~$3K. You have an LLC and a tested prototype. Likely transferable to a different venture.
- Stop after Phase 3 if Kickstarter fails: you spent ~$15K. Painful but recoverable — tooling can be sold, parts can be inventoried, brand can be sold to someone with distribution.

---

## What's on Smith's plate next (today/this week)

I will, in the order listed, between now and Wednesday:

1. **Phase-2 patent search** — additional Google Patents + USPTO TESS queries on launcher-mechanism prior art (spring-loaded toy projectiles, water-actuated safety interlocks). Write up findings as a follow-on memo.
2. **Brand candidate brainstorm** — 8-10 name candidates, each USPTO-TESS-cleared and .com-available at search time. Aesthetic per the Braun/Apple brief.
3. **SVG concept sketches** — 2-3 launcher silhouette concepts drawn as SVG renders the son can use as a visual starting point in Fusion 360. NOT CAD-quality — concept-level only.
4. **Compile a teardown brief** — what to look for inside the Toypedo Blast when you crack it open in Week 2.
5. **HubSpot task** — create a task on Duncan tracking the patent attorney engagement (due Week 4).

---

## Open questions for Duncan

These need your input before I proceed past today:

1. **Working brand name preference / vibe.** Direction so far: "Mac / Braun." Any specific words, themes, or feelings you want me to lean toward? (e.g., "ocean," "physics," "calm," "Aerobie-adjacent")
2. **Budget ceiling for Phase 1+2 (Weeks 1-7).** I have ~$3K total as the working number. Confirm or correct.
3. **Patent attorney pick.** Do you have a Florida IP attorney already? If not, I can shortlist 3 based on PBC bar listings.
4. **Son's CAD experience level.** Has he used Fusion / Tinkercad before? Affects Week 1 tutorial sequence.
5. **Risk appetite on Phase 3.** Are you willing to commit ~$15K to tooling + CPSC even if Kickstarter is unproven? Or do you want pre-launch validation (waitlist + landing page) BEFORE the tooling money is spent?

---

*Plan drafted by Smith on Sat 2026-05-23 15:20 EDT. All figures are mid-market estimates and must be verified with real quotes before commitment. Patent findings are verified to the extent shown above; FTO clearance requires attorney-led search before tooling spend.*
