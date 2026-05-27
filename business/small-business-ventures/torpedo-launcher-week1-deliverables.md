# Torpedo launcher — Week 1 deliverables

**Drafted by Smith, Sat 2026-05-23 ~15:30 EDT.** Continuing from `torpedo-launcher-90-day-plan.md`. All facts here are either verified via live search this session or explicitly labeled as estimate / hypothesis / needs-verification.

---

## 1. Phase-2 patent search — launcher mechanism prior art

**Search method:** Google Patents + web verification. Not a substitute for a freedom-to-operate (FTO) opinion from a registered patent attorney before tooling commitment.

### Public-domain (expired) prior art — safe to learn from

| Patent | Year | What it covers | Status (verified this session) |
|---|---|---|---|
| [US2627853](https://patents.google.com/patent/US2627853) | 1953 | Toy submarine with internal compression-spring torpedo launching tube + trigger | **EXPIRED** — public domain |
| [US4076006A](https://patents.google.com/patent/US4076006A/) | 1976 | Toy rocket with pneumatic launcher (pump-up canister) | **EXPIRED** — public domain |
| [US4411249A](https://patents.google.com/patent/US4411249) | 1983 | Toy glider with pneumatic launcher | **EXPIRED** — public domain |
| [US5553598A](https://patents.google.com/patent/US5553598A/en) | 1996 | Pneumatic launcher for a toy projectile (plunger → piston sleeve → nozzle → projectile) | **EXPIRED – Lifetime** — public domain |

**Plain-English meaning:** the *classic rigid-tube pneumatic launcher* (think bicycle-pump style: hand pump → compressed air chamber → trigger → projectile leaves a rigid barrel) is **free to use**. So is *spring-driven launching from a tube*. So is a *bow/stretched-elastic projectile launcher*. None of the foundational mechanics are still under patent.

### Active patents — design around these

| Patent | Year filed | Assignee | What to avoid |
|---|---|---|---|
| [US8517004B2](https://patents.google.com/patent/US8517004) | 2011 | **Zing Toys, Inc.** | Pneumatic launcher with a *flexible closed-cell foam barrel that bends ≥90° without blocking airflow*. **Don't make a bendy-tube launcher.** A rigid barrel sidesteps this. |
| [US8485168B2](https://patents.google.com/patent/US8485168) | ~2010 | (Slingshot toy patentee) | A specific safety mechanism where projectiles have *slotted channels that temporarily attach to elastomeric elements during launching*. **Don't copy that exact channel-and-elastomer projectile interface.** Generic elastic-band slingshots predate this and are fine; the specific attachment geometry is what's protected. |
| [USD738441S1](https://patents.google.com/patent/USD738441S1/en) | 2014 | (Design patent) | *Ornamental design only* — a "bow configuration" toy pneumatic launcher's specific look. We're going Braun/Apple, so no overlap, but worth knowing design patents exist in this space. |
| [TOYPEDO®](https://patents.google.com/patent/US6699091B1) trademark | — | SwimWays / Spin Master | Word mark only. Don't name our torpedo "Toypedo," "Torpedo Blast," or anything confusingly similar. The underlying *torpedo geometry* patent (US6699091B1) **expired in November 2019** — verified in earlier feasibility memo. |

### What this gives us

A **rigid-barrel pneumatic launcher** (Concept A or B) is on the safest path. A **draw-back elastic-band launcher with a generic projectile cradle** (Concept C) is the absolute lowest risk and lowest cost — at the expense of "magic" range. My recommendation in the 90-day plan stands: pick the mechanism after the Toypedo Blast teardown tells us what range / pressure we need to beat.

**Honest gap:** I did not exhaustively search WIPO / EPO / design patents internationally. The attorney FTO ($500-1,500 budgeted in Phase 2) should run that pass before tooling.

---

## 2. Brand name shortlist — 10 candidates, .com verified available

**Method:** brainstormed 35+ names, ran live `whois` against each, kept the 10 that returned "No match" (= unregistered as of this session, 2026-05-23). **Trademark clearance is NOT done** — that requires USPTO TESS+ and ideally an attorney. Treat this as a "the .com is open" shortlist, not a "we own this name" list.

| # | Name | .com (verified avail.) | Vibe / read |
|---|---|---|---|
| 1 | **Velodart** | velodart.com ✅ | Latin "velo-" (swift) + dart. Short, premium, mac-clean. My top pick. |
| 2 | **Plumedive** | plumedive.com ✅ | "Plume" evokes the graceful arc underwater. Elegant, two-syllable. |
| 3 | **Glidewerks** | glidewerks.com ✅ | Germanic "werks" = engineering pedigree (Braun/Leica feel). |
| 4 | **Plumewerks** | plumewerks.com ✅ | Same vibe as #3, softer. |
| 5 | **Sonarklab** | sonarklab.com ✅ | Tech-forward, lab/origin-story-friendly. |
| 6 | **Plumesub** | plumesub.com ✅ | Compact. Reads premium. |
| 7 | **Plumeaqua** | plumeaqua.com ✅ | Water-native, soft. |
| 8 | **Glideaqua** | glideaqua.com ✅ | Action + element. Descriptive. |
| 9 | **Dartaqua** | dartaqua.com ✅ | Most product-literal; weaker as a brand. |
| 10 | **Sonaraqua** | sonaraqua.com ✅ | Most distinctive of the "-aqua" set. |

**Top 3 to discuss:** Velodart, Plumedive, Glidewerks. Each evokes a different brand archetype:
- **Velodart** = tech / sport (think Velocity meets Aerobie)
- **Plumedive** = design / craft (think Muji meets Aesop)
- **Glidewerks** = engineering / heritage (think Braun meets Leica)

**Next step before committing to a name:** USPTO TESS+ search by the attorney engaged for FTO. Adds maybe $200-400 to the legal scope. Don't buy the .com until cleared — domain squatters watch trademark filings.

---

## 3. Three launcher silhouette concepts (SVG)

Three rough visual concepts saved as SVG, sized for inclusion in a pitch deck. All deliberately rendered in the Braun / Apple visual language: matte off-white or charcoal bodies, single signal-orange accent, no decals, monogram-only branding. **These are silhouettes, not engineering drawings** — they communicate proportion and color, not internal mechanism.

| File | Concept | Best for |
|---|---|---|
| [torpedo-launcher-concept-A-pistol.svg](torpedo-launcher-concept-A-pistol.svg) | **A: Pistol-grip pneumatic.** Single integrated cylinder + trigger + pump plunger at rear. Off-white body, orange muzzle ring + pressure dot. | One-hand operation, intuitive for kids, classic familiar form |
| [torpedo-launcher-concept-B-tube.svg](torpedo-launcher-concept-B-tube.svg) | **B: Two-hand tube (T1000-inspired).** Long charcoal cylinder, side-pump action, palm "FIRE" trigger at rear cap. Pressure window readable underwater. | Premium pitch, hero photography, "magic" reveal moment |
| [torpedo-launcher-concept-C-elastic.svg](torpedo-launcher-concept-C-elastic.svg) | **C: Elastic-band slingshot ring.** No pressure system, just stretched silicone bands + cradle. Sea-foam + cream body. | Cheapest tooling, fastest MVP, naturally child-safe |

**Smith's read:**
- **Concept B is the "magic" version** — visually distinctive, photographs beautifully, justifies $30-40 price. Highest tooling cost and most engineering risk.
- **Concept A is the safe commercial version** — familiar pistol form lowers the cognitive lift at retail, kids "get it" instantly.
- **Concept C is the validation MVP** — could ship a 3D-printed version in 3 weeks to test product-market fit before any tooling commitment. If demand signal is strong with C, we know B is worth the spend.

My suggested path: **prototype C first (Phase 1), then B for the brand hero (Phase 2-3).**

---

## 4. SwimWays Toypedo Blast — teardown brief

**Status:** I have not physically taken one apart. This is the *teardown plan* for when Duncan or his son does so, plus what I can infer from public listings, product specs, and Amazon-review patterns. Every spec below is labeled by source.

### Acquire

- **Product:** SwimWays Toypedo Blast — "Underwater Torpedo Launcher" (per Amazon listing; verify exact SKU at purchase)
- **Approx. retail:** $15-25 (verify at point of purchase — don't quote this number to anyone until confirmed)
- **Source:** Walmart, Target, Amazon, or pool-supply retailer
- **Action:** buy 2 units (one for teardown, one for control + pool test reference)

### What to capture before disassembly

1. **Unboxing video** (phone, 4K). Packaging is part of the competitor read — note how it feels in-hand, what the instructions assume about the buyer.
2. **Weight, in grams,** on a kitchen scale. Empty + with included torpedoes.
3. **Range test, pre-teardown.** 5 shots in a pool, measured underwater distance. Record both *peak* and *typical* range. This is the number we have to beat.
4. **Trigger-pull force** (rough — pinch with a luggage scale if available). Tells us if a 7-year-old can operate it solo.
5. **Reload time** — how long from "torpedo retrieved" to "next shot fired."
6. **Pressure source.** Spring? Compressed air via pump? Single-shot elastic? Read the manual; visible from the body design.

### Teardown sequence

1. **Remove visible fasteners** first. Most pool toys use either (a) Phillips machine screws into brass inserts, or (b) snap-fit + ultrasonic weld. Photograph the bottom face for any hidden screws under stickers.
2. **If snap-fit:** use a plastic spudger along the seam. Note force needed. If it requires a knife, **stop and document** — that means the unit isn't meant to be opened, which often correlates with cost-cutting (no service-life expected).
3. **Lay every part on graph paper, label A1, A2, A3…** Photograph from above with each labeled.
4. **Count and categorize:** rigid plastic parts, soft/elastomer parts, metal parts, fasteners, springs, seals/O-rings.
5. **For each major part, note:** material guess (ABS / polypropylene / TPE / nitrile rubber), manufacturing process guess (injection-molded / blow-molded / extruded / die-cut), wall thickness in millimeters.
6. **Mechanism map.** Draw the energy path: hand input → storage (spring / air / elastic) → release (trigger geometry) → projectile coupling → projectile exit.

### What we're looking for (the read)

| Question | Why it matters |
|---|---|
| **Total part count?** | <12 parts = optimized for cost; >20 parts = room for us to simplify and undercut on bill-of-materials |
| **Number of distinct injection-mold tools required?** | Drives our tooling cost estimate (~$3-8K per cavity mold, China, mid-market estimate) |
| **O-ring or seal anywhere?** | If yes → pneumatic (pressure-based). If no → spring or elastic |
| **Trigger feel — crisp or mushy?** | Mushy = the user-experience gap we'd exploit. Crisp = harder to beat without engineering investment |
| **Is the torpedo proprietary or generic foam?** | Razor-and-blades model viable if proprietary; less so if generic |
| **What feels cheap?** | Per Duncan's "2000-era Windows PC" critique — what *specifically* signals cheapness? Logo placement? Color choice? Seam lines? Sticker decals? Texture? List every offender. Those are our design opportunities. |

### Open weaknesses (from public Amazon-review patterns — labeled as "review-derived, not verified by us")

These are themes that show up across multiple Amazon reviews of pool-torpedo launchers in the SwimWays product family. **They are crowd-sourced complaints, not lab findings** — useful as hypotheses to verify in our own test:

- **Short range.** Multiple reviewers report under-10-foot underwater distance vs. marketing claims of further. Verify with our own measurement.
- **Mechanism failure after a season.** Reports of the spring/pump losing tension or the trigger jamming after 2-3 months of pool use. Indicates chloride corrosion or fatigue. Our spec should target a 3-summer minimum life.
- **Torpedoes float away / get lost.** No retrieval line, no high-visibility marking. Trivial fix on our side — bright accent color + optional retrieval string.
- **Plastic feels brittle.** Reviewers note the launcher housing cracks when stepped on at the pool edge. Material upgrade (PC/ABS blend instead of straight ABS) addresses this for pennies per unit.
- **Decals peel.** Chlorine-printed graphics fade in one season. Our brand decision (laser-etched monogram only, no decals) sidesteps this entirely and reads as premium at the same time.

### Deliverable from the teardown

A 2-page PDF brief that becomes Slide 4-5 of the Kickstarter / investor deck:
- **Slide 4:** "Here's what's in the box today" — annotated teardown photo, part count, mechanism diagram, weight, range
- **Slide 5:** "Here's what we changed and why" — side-by-side: cheap-feeling element → our premium replacement, with the cost delta per unit

I can draft this once the physical teardown happens. Estimated 3 hours of writing time once photos and notes are in hand.

---

## 5. What's next from Smith

These are queued for the next time we work on the torpedo launcher venture, no Duncan input needed first:

1. **Draft a Toypedo Blast purchase order** in the form of a $40 line-item budget request (covers 2 units + shipping) — wait for Duncan to greenlight before ordering.
2. **Sketch 3D-printable Concept C** in detail (dimensioned line drawings) so it can be sent to a print farm or a local maker — does not require Duncan's son to have CAD experience.
3. **Build the FL IP attorney shortlist** — 3 Palm Beach IP attorneys with toy / consumer product experience, with consultation fees and contact info, ready for Duncan to pick one.
4. **Outline the Kickstarter prelaunch page copy** — headline, sub-headline, the "magic moment" video brief, the 3-tier pledge structure.

## Open questions (still pending from prior turn)

1. Which brand vibe — Velodart (tech/sport), Plumedive (design/craft), or Glidewerks (engineering/heritage)?
2. Confirm ~$3K ceiling through end of Phase 2 (FTO + LLC + pool test)?
3. Want the FL IP attorney shortlist drafted now, or wait until after teardown?
4. Son's CAD experience level — Tinkercad-savvy? Fusion-capable? Or starting cold?
5. Phase 3 commercialization path — Kickstarter prelaunch (validate demand first) or direct-to-Shopify + paid Meta (faster, riskier)?

---

*All numbers labeled with explicit source. All patents verified live this session. Brand `.com` availability verified via `whois` this session. SVGs are silhouette-level only — engineering drawings come after Concept selection and FTO clearance.*
