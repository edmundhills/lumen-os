<!--
SPDX-FileCopyrightText: 2026 Lumen OS contributors

SPDX-License-Identifier: GPL-3.0-or-later
-->

# windows-setup

Lumen Setup for Windows: a Windows program that gets a PC ready for Lumen before Lumen is on it. It checks the hardware against the [hardware database](../hardware/); checks BitLocker, Fast Startup, Secure Boot and the Microsoft UEFI CA 2023; shows where the BitLocker recovery key is; and, to install alongside Windows, shrinks the Windows partition and sets the Windows clock to UTC. Then it downloads Lumen, verifies the download and writes the install USB. Every change to Windows has its own confirm button.

- **Language:** C++ and Qt, forked from Fedora Media Writer.
- **Runs on:** Windows.
- **Ships as:** a code-signed Windows program, built on a GitHub Actions Windows runner, outside the image.
- **Licence:** Fedora Media Writer is GPL-2.0-or-later. The forked files keep their notices, and Lumen's changes are GPL-3.0-or-later ([ADR 0003](../docs/decisions/0003-licence.md)).
- **Steps:** 7.9. It needs a Windows code-signing certificate from the owner, or SmartScreen warns users ([risk 9](../docs/risks.md#9-windows-code-signing-for-lumen-setup)).

Spec: [Lumen Setup for Windows](../docs/spec.md#lumen-setup-for-windows). Architecture: [4.9 Windows apps and switching](../docs/architecture.md#49-windows-apps-and-switching), [9.10 Built outside the image](../docs/architecture.md#910-built-outside-the-image).
