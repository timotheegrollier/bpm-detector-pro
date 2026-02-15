#!/usr/bin/env python3
"""Compatibility launcher for older scripts. Use bpm_gui.py as canonical entrypoint."""

from bpm_gui import BPMApp


if __name__ == "__main__":
    app = BPMApp()
    app.mainloop()
