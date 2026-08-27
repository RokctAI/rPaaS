# Task Brief: Hoist a Shared GlanceCard Shell into base_sdk

> Self-contained brief for a fresh session. Read in full; should not require the
> conversation that produced it. Two real, confirmed facts motivate this: (1)
> `launch_sdk`'s home page template
> (`core/launch/dart/templates/pages/home.dart`) has a live integration marker
> (`// @launcher-glance-imports` / `// @launcher-glance`) that used to be filled
> by retired `core_sdk`'s glance-card widget — now empty in all 5 apps composing
> `launch_sdk` (`launcher`, `manager`, `pos`, `launch_deliver`,
> `launch_manager`), since `core_sdk` was retired during the refork. (2)
> `lms_sdk` just built its own fresh glance card for Supacharge's
> session-scheduling UI (P4 work, `lms/dart/lib/src/presentation/pages/schedule/`),
> including a `GlanceSignal` host seam anticipating exactly this kind of external
> wiring. Two SDKs need the same UI pattern; right now there's zero shared code
> between them.

## What to build

A **generic, presentation-only `GlanceCard` shell** in `base_sdk` — layout, the
"collapse to nothing when quiet" behavior, and whatever visual chrome is
genuinely common — with **no business logic baked in**. Each feature SDK supplies
its own content through its own interface, matching ADR-005 (base_sdk is the
only cross-SDK-safe dependency; feature SDKs never import each other; the host
wires concrete adapters).

Concretely:

1. Read `lms_sdk`'s existing glance-card implementation (P4 work) and
   `launch_sdk`'s dead marker/old `core_sdk` widget to find the genuinely shared
   shape: card container, empty/quiet state, expand/collapse, whatever's truly
   generic across both use cases. Note: the old `core_sdk` reference file this
   brief originally pointed at
   (`core/core/dart/templates/pages/launch/widgets/glance_card.dart`) no longer
   exists — `core/core` was deleted outright once confirmed fully retired and
   superseded. The shell this brief asked for has since been built at
   `core/base/dart/lib/src/presentation/components/glance_card.dart`
   (exported from `base_sdk`'s barrel) — read that as the current reference
   instead.
2. Design the content-injection interface — each consuming SDK provides a
   widget/data adapter (matching how `lms_sdk`'s `GlanceSignal` seam already
   anticipates external content), not a fixed set of fields. Don't assume
   `lms_sdk`'s specific content shape (door countdown, skip-lock notice) is the
   general case — those are `lms_sdk`-specific, they stay in `lms_sdk`.
3. Build the shell in `base_sdk`, export it, and:
   - Refactor `lms_sdk`'s existing glance card to use the shared shell instead
     of its own from-scratch implementation, if that's a clean fit without
     regressing P4's work — verify with existing tests, all should still pass.
   - Fill `launch_sdk`'s dead `@launcher-glance` marker with a real adapter
     using the shared shell, giving `launcher`/`manager`/`pos`/`launch_deliver`/
     `launch_manager` a working glance card again for the first time since
     `core_sdk` retired. Determine what content those apps actually need
     there — check what the old `core_sdk` widget rendered for a starting point,
     but don't assume it's still correct/relevant without verifying against
     what those apps currently have available.

## What NOT to do

- Don't put any feature-specific logic in `base_sdk`'s shell — no lesson/schedule/
  door-policy concepts, no launch-specific concepts. If content logic doesn't
  generalize, it stays in the consuming SDK.
- Don't regress `lms_sdk`'s P4 work — its glance card and tests are done and
  verified; any refactor to use the shared shell must keep all existing tests
  passing, not just look similar.
- Don't guess what `launch_sdk`'s glance card should show — check what data/
  providers are actually available in the apps that compose `launch_sdk` before
  designing content for it.

## Deliverable

`base_sdk`'s `GlanceCard` shell built and exported; `lms_sdk` verified still
passing all tests (refactored to use it, or left as-is with a clear reason if
refactoring isn't a clean fit); `launch_sdk`'s dead marker filled with a real,
working adapter, verified via a clean recompose of at least one app that uses
it (e.g. `manager` or `pos`) with `flutter analyze` at 0 errors. Report back
with evidence for each piece.
