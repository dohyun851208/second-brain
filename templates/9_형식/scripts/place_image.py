#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public entry point for measured image placement in HWP/HWPX forms.

The implementation remains in ``place_signature.py`` so existing Second Brain
vaults and commands keep working. New workflows should call this generic name.
"""

from __future__ import annotations

from place_signature import main


if __name__ == "__main__":
    raise SystemExit(main())
