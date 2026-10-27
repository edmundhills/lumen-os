<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# hardware

`hardware.json`, the hardware database: devices and machines that are known good, that have known issues with workarounds, or that are known broken. lumen-hwd compares a machine with it for the hardware report (green, amber or red per device) and for Settings, and Lumen Setup for Windows uses the same file before Lumen is installed.

- **Ships as:** RPM `lumen-hardware-data`, installed at `/usr/share/lumen/hardware.json` and built in the image's `build-rust` stage. Lumen Setup for Windows carries a copy.
- **Checked:** against its JSON schema in CI.
- **Steps:** 6.11 (the database and the compare logic, including the Microsoft UEFI CA 2023 check) and 6.12 (the hardware report app).

Spec: [Hardware report (live USB)](../docs/spec.md#hardware-report-live-usb). Architecture: [lumen-hwd](../docs/architecture.md#lumen-hwd-orglumenhardware1).
