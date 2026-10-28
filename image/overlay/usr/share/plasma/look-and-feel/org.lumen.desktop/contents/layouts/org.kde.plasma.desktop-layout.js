// SPDX-FileCopyrightText: 2026 Lumen OS contributors
//
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The desktop layout a new user starts with: Lumen's interim top bar, in place
// of Kinoite's stock bottom panel. It is one 32 px bar along the top of the
// main screen, where lumen-shell's top bar will go, built from stock Plasma
// widgets: the app menu and open windows on the left, then the system tray
// (Wi-Fi, sound, battery, notifications) and the clock. lumen-shell replaces
// it at step 4.2. The owner chose this interim bar over a bare desktop on
// 2026-10-27, so Wi-Fi, sound and notifications keep working while Phases 1
// to 3 are tested.
//
// Plasma runs this once, the first time a user's session starts.

var panel = new Panel;
panel.location = "top";
panel.height = 32;

panel.addWidget("org.kde.plasma.kickoff");
panel.addWidget("org.kde.plasma.icontasks");
panel.addWidget("org.kde.plasma.marginsseparator");
panel.addWidget("org.kde.plasma.systemtray");
panel.addWidget("org.kde.plasma.digitalclock");

// Every desktop shows the wallpaper picture, as in Fedora's layout.
var desktopsArray = desktopsForActivity(currentActivity());
for (var j = 0; j < desktopsArray.length; j++) {
    desktopsArray[j].wallpaperPlugin = "org.kde.image";
}
