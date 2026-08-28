# CLAUDE.md — OpenMANET Raspberry Pi 5 Project Authority

## Project Mission

Port the existing OpenMANET firmware to Raspberry Pi 5 8GB while preserving existing Raspberry Pi 4 support.

Primary new hardware target:

- Raspberry Pi 5 8GB
- Seeed Studio WM1302 Raspberry Pi HAT
- Wio-WM6108 Wi-Fi HaLow module
- Morse Micro MM6108
- SPI interface
- United States 900 MHz configuration

This is a PORT of the existing OpenMANET source, not a redesign from scratch.

Preserve existing upstream architecture wherever practical.

Primary repository:

C:\AI-Projects\OpenMANET-Pi5\firmware

Development branch:

pi5-wm6108-port

Official upstream:

https://github.com/OpenMANET/firmware

Expected upstream baseline family:

OpenMANET 24.10

Important existing Pi 5 work to investigate:

https://github.com/OpenMANET/firmware/pull/46

PR #46: Rpi 5 BCM2712 & Heltec HC01P Support

Do not blindly merge PR #46. Audit and selectively reuse appropriate work.

Our required production HaLow path is:

Raspberry Pi 5
+
Seeed WM1302
+
Wio-WM6108 / MM6108
+
SPI

The Heltec HC01P is not the primary production target.

---

## Owner Interaction Policy

The owner is extremely busy.

MINIMIZE OWNER INTERACTION.

The main Claude agent must make routine engineering decisions autonomously.

Default workflow:

INSPECT
→ DELEGATE
→ DECIDE
→ IMPLEMENT
→ BUILD
→ DIAGNOSE
→ FIX
→ RETEST
→ CONTINUE

Do not ask the owner to choose routine implementation details.

Do not ask whether to:

- inspect another file
- use a helper
- run another build
- inspect logs
- retry a failed build
- perform ordinary debugging
- modify normal target-specific configuration
- research upstream
- create normal Git checkpoints
- update project context
- make safe reversible engineering decisions

Make those decisions yourself.

The owner should only be interrupted when genuinely required for:

1. physical hardware interaction;
2. credentials or external authorization;
3. consequential irreversible actions;
4. material cost or hardware-design choices;
5. a genuine technical blocker after reasonable autonomous investigation.

When owner action is required, request ONE concise action at a time.

---

## Main Agent and Subagents

The main Claude agent owns the project.

Use subagents/helpers aggressively when parallel work reduces elapsed time.

The owner does NOT coordinate helpers.

Helpers should be used for tasks such as:

- repository architecture mapping
- PR #46 audit
- OpenWrt BCM2712/RP1 research
- Morse Micro/MM6108 analysis
- device-tree/SPI analysis
- build failure analysis
- regression review
- independent validation

The main agent must collect findings and make final decisions.

Do not allow important information to exist only inside helper private context.

---

## Parallel Workstreams

Use workstreams equivalent to:

### OpenMANET Architecture

Map existing:

- Raspberry Pi 4 / BCM2711 support
- target profiles
- setup/build scripts
- image definitions
- device tree
- overlays
- GPIO
- SPI
- Morse Micro packages
- MM6108 firmware
- BCF
- WM1302
- Wio-WM6108
- openmanetd
- 802.11s
- batman-adv
- network configuration

### PR #46 Audit

Categorize relevant changes as:

REUSE
MODIFY
DO NOT USE
NEEDS TESTING

Separate generic BCM2712/RP1 support from Heltec-specific changes.

Check for:

- Pi 4 regressions
- WM1302/Wio-WM6108 regressions
- outdated changes
- unresolved review concerns

### OpenWrt BCM2712 / RP1

Investigate only what materially affects OpenMANET:

- BCM2712
- RP1
- SPI controllers
- GPIO
- pinctrl
- IRQ
- device tree
- overlays
- kernel modules
- Ethernet
- onboard Wi-Fi
- image generation
- boot behavior

### Morse Micro / MM6108

Trace:

- SPI bus
- chip select
- reset
- IRQ
- wake
- GPIO
- driver initialization
- MM6108 firmware
- BCF
- mac80211
- HaLow interface creation

### Regression / Validation

Verify Raspberry Pi 4 support remains intact.

---

## Engineering Priority

This is a focused 2–4 day development sprint.

Prioritize working hardware over perfection.

Order:

1. BCM2712/Pi 5 target
2. successful complete firmware build
3. Pi 5 boot
4. RP1/SPI/GPIO
5. WM1302 + Wio-WM6108 initialization
6. Morse Micro MM6108 stack
7. OpenMANET services
8. 802.11s / batman-adv
9. real two-node HaLow/OpenMANET connectivity

Avoid unrelated refactoring and cosmetic work.

---

## Raspberry Pi 4 Preservation

Do not turn the repository into a Raspberry-Pi-5-only fork.

Required desired state:

Pi 4 + WM1302 + Wio-WM6108
remains supported

AND

Pi 5 + WM1302 + Wio-WM6108
becomes supported

Prefer target-specific changes.

If shared code changes are necessary:

- understand why;
- keep changes minimal;
- evaluate Pi 4 effects;
- validate BCM2711;
- document the decision.

---

## Build Rules

Do not stop after the first build failure.

For failures:

1. capture relevant error;
2. classify failure;
3. inspect source/logs;
4. delegate targeted research if useful;
5. make the safest reasonable fix;
6. use targeted rebuilds when efficient;
7. retry;
8. continue.

Perform a trustworthy full build before declaring BUILD VERIFIED.

OpenWrt compilation is Linux-oriented.

Use WSL2/Linux where technically appropriate.

The Windows repository must remain isolated from unrelated projects.

Never access:

C:\Websites

or Patriot's Craft repositories.

If a Linux-native build tree is needed for performance/correctness, design and manage it safely without creating confusing divergent authoritative copies.

---

## Build vs Hardware Validation

Always distinguish:

BUILD VERIFIED

from:

HARDWARE VERIFIED

A successful image build does not prove:

- Pi 5 boot
- RP1 SPI operation
- MM6108 initialization
- RF functionality
- mesh association

When physical testing becomes necessary, ask the owner only for the minimum next hardware action.

---

## Git Safety

Never:

- force-push
- rewrite existing history
- delete known-good Pi 4 support
- commit directly to upstream branches

Use logical milestone commits.

Examples:

- BCM2712 target groundwork
- Pi 5 image support
- RP1/SPI support
- MM6108/WM1302 integration
- OpenMANET networking
- validation/regression fixes

Avoid meaningless tiny commits.

---

## Persistent Context

Maintain:

PI5_PORT_STATUS.md

It is the authoritative current-state file.

Keep it concise.

It should contain:

- current objective
- branch
- upstream baseline commit
- PR #46 reference
- hardware target
- completed milestones
- implementation state
- most recent successful build
- most relevant current failure
- hardware validation completed
- hardware validation required
- blockers
- important technical decisions
- exact next engineering action

Do not make the owner reconstruct history from chat.

At the start of future sessions:

1. read CLAUDE.md;
2. read PI5_PORT_STATUS.md;
3. run git status;
4. confirm branch;
5. inspect recent relevant commits;
6. resume from exact next action.

Before a meaningful stopping point:

1. update PI5_PORT_STATUS.md;
2. preserve important decisions;
3. preserve blocker information;
4. preserve exact next action;
5. create a logical Git checkpoint when appropriate.

---

## Model Strategy

Default main model:

Opus 5
1M context
High effort

Use Opus for normal engineering, implementation, coordination, builds, integration, and debugging.

Fable 5 is an escalation model.

Recommend Fable only for genuinely difficult blockers such as:

- unresolved BCM2712 architecture problems
- difficult RP1/device-tree issues
- difficult kernel problems
- difficult Morse Micro/MM6108 problems
- complex failures Opus has reasonably investigated but cannot resolve

Do not waste Fable on routine builds, simple edits, documentation, or ordinary compiler failures.

If escalation is warranted, tell the owner exactly:

MODEL SWITCH RECOMMENDED: Fable 5

Give one concise reason.

Before requesting a model switch:

- update PI5_PORT_STATUS.md;
- preserve Git state;
- preserve relevant logs;
- record exact blocker;
- record exact next action.

When the difficult issue is resolved, recommend:

MODEL SWITCH RECOMMENDED: Opus 5

Sonnet 5 may be used for low-complexity helper work, repetitive validation, cleanup, and documentation where appropriate.

Do not frequently interrupt the owner for model changes.

---

## Deferred Scope

Do NOT implement during the core Pi 5 port:

- Android
- ATAK running locally
- Android virtualization
- HDMI ATAK display
- EUD redesign
- VLM redesign
- enclosure redesign
- unrelated UI changes
- unrelated camera work

These are later phases.

Avoid unnecessarily blocking future expansion toward integrated commercial-MANET-radio-style capabilities.

---

## Phase 1 Definition of Done

Phase 1 requires, or explicitly awaits physical validation of:

- Raspberry Pi 5 BCM2712 target
- successful OpenMANET firmware build
- bootable Pi 5 image
- Pi 4 support preserved
- Pi 5 WM1302/Wio-WM6108 SPI support
- Morse Micro MM6108 driver
- required MM6108 firmware
- correct BCF
- openmanetd
- batman-adv
- mesh functionality
- Pi 5 hardware boot
- HaLow interface initialization
- two-node mesh association
- BATMAN path
- IP traffic across mesh

Do not falsely claim hardware validation from software-only evidence.

---

## Owner Reporting Style

Do not continuously narrate progress.

Work autonomously for meaningful stretches.

When reporting to the owner, use:

COMPLETED:
...

CURRENT:
...

BLOCKER:
Only when applicable.

OWNER ACTION REQUIRED:
Only when genuinely required.

NEXT:
What will continue automatically.

Do not request approval for the normal next engineering step.
