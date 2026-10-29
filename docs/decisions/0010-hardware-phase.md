<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# 0010. A phase of its own for making full use of each device

- Status: **Accepted** (2026-10-29).
- Deciders: the owner, who asked for it; lead engineer (Claude), who placed and scoped it.

## Context

The owner asked for a phase in which Lumen learns to use everything the hardware it runs on can do: a good webcam, and any feature that is specific to a device.

The spec already asks for some of it: fingerprint readers, touchpad gestures, pens, printers, Bluetooth audio and the NVIDIA driver, plus a hardware report that marks each device green, amber or red. No phase owned making those features work well, though, and others weren't named at all. Windows users get them from their laptop maker's drivers and tuning, and miss them when they move to Linux:

- **Cameras.** Many laptops since about 2021 have MIPI cameras behind Intel's IPU6 or IPU7 instead of USB webcams. On Linux these work only through libcamera, with image tuning for some sensors and not yet for others.
- **Sound.** Laptop speakers and microphones are tuned per model on Windows, often with the maker's audio processing. Without it they sound thin on Linux.
- **Other device features:** HDR, variable refresh and high refresh rates; automatic brightness; pens and 2-in-1 tablet mode; vendor keys such as camera and microphone mute; battery charge limits and performance modes; NPUs and the GPU's video engines.

## Decision

1. **A new Phase 8, "Hardware: full use of each device"**, before hardening and the release, so that v0.1 ships with it and the security and accessibility reviews cover what it adds. Its steps are in PROGRESS.md and the spec's Phase 8 list:
   - `docs/hardware.md`, which the owner reviews;
   - device profiles in `hardware/hardware.json` that lumen-hwd applies by itself;
   - one step each for cameras, sound, displays, input, power and heat, graphics and accelerators, and connections;
   - the Drivers & Hardware page in Settings;
   - tests, and an acceptance check on the reference laptops.
2. **A device gets its best settings without the user asking.** lumen-hwd applies the profile for the model on the first boot and when hardware changes, and Settings says what it changed and why.
3. **Renumbering:** the old Phase 8 (hardening, accessibility, performance) is now Phase 9, and the old Phase 9 (release v0.1) is now Phase 10; their steps move with them, so the old 8.2 is now 9.2 and the old 9.1 is now 10.1. The spec, PROGRESS.md, the architecture, the risk register and `docs/README.md` use the new numbers. Accepted ADRs aren't rewritten: ADRs 0001 to 0009 use the old numbers.

## Consequences

- v0.1 comes one phase later.
- Each device feature needs real hardware to finish. The reference laptops (the spec's hardware lab) must be chosen at step 8.1, and the owner, or testers with those laptops, run the acceptance check. CI can only test what can be emulated, such as a virtual camera, touchpad and pen.
- Some vendor features need tools from outside Fedora, such as `asusctl` for ASUS laptops. Each one goes through the package manifest, and an ADR when it needs a new repository.
- Where Linux can't yet drive a device feature, the hardware report and Settings say so plainly, as the ratings for Windows apps do.
