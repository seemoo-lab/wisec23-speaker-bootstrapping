# Linux Client

This folder contains the Linux client implementation. The GUI is built on `GTK4/libadwaita`.

## Dependencies

The client is distributed as a Flatpak. The sole requirement on the host system is the usage of NetworkManager for WiFi control.

## Building

Use GNOME Builder to open the project. GNOME Builder supports Flatpak building out-of-the-box. Execute the program from Builder for debugging and testing purposes or export it as a Flatpak file for distribution.

## Overview

The JSON files in the root directory describe dependencies. The `src` directory contains the Python code, a libquiet profiles file, UI definitions and the wordfile.
To edit the UI, use cambalanche, the GTK4 UI editor.
