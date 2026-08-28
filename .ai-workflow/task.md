# CURRENT TASK — OPENMANET RASPBERRY PI 5 PORT

Read CLAUDE.md in full before beginning.

The immediate objective is to begin and autonomously execute the Raspberry Pi 5 OpenMANET port.

Primary target:

Raspberry Pi 5 8GB
+
Seeed Studio WM1302 HAT
+
Wio-WM6108 / Morse Micro MM6108
+
SPI
+
U.S. 900 MHz configuration

Preserve Raspberry Pi 4 support.

This is based on the existing OpenMANET source code.

Do NOT redesign OpenMANET from scratch.

Investigate and selectively reuse existing Raspberry Pi 5 work from:

https://github.com/OpenMANET/firmware/pull/46

Do not blindly merge it.

Begin immediately.

Initial work:

1. Verify repository and Git state.
2. Confirm branch pi5-wm6108-port.
3. Record current baseline commit and remotes.
4. Create or update PI5_PORT_STATUS.md.
5. Launch useful parallel subagents/helpers.
6. Map current Pi 4/BCM2711 OpenMANET implementation.
7. Fetch and audit PR #46.
8. Compare PR #46 with current 24.10 upstream.
9. Separate generic BCM2712/RP1 work from Heltec-specific work.
10. Determine exactly what is required for WM1302 + Wio-WM6108 on Pi 5.
11. Proceed into implementation without waiting for routine owner approval.
12. Build using the appropriate Linux/WSL environment.
13. Diagnose failures autonomously.
14. Fix and rebuild.
15. Continue until:
    - a meaningful hardware-validation checkpoint is reached;
    - a genuine owner-required blocker exists;
    - a Fable escalation is genuinely justified; or
    - the Phase 1 objective is complete.

Do not stop merely to give the owner an architecture report if implementation can safely continue.

Use safe defaults.

Use helpers aggressively.

Minimize owner interaction.

Maintain:

PI5_PORT_STATUS.md

and:

.ai-workflow\last-claude-report.md

At meaningful handoff points.

PRIMARY MISSION:

Get the existing OpenMANET firmware running on Raspberry Pi 5 8GB with the existing Seeed WM1302 + Wio-WM6108 SPI HaLow hardware while preserving Raspberry Pi 4 support.
