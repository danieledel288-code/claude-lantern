#!/usr/bin/env python3
"""Manual install without the plugin marketplace. See README.

    python install.py [hal|john|guy|default]
    python install.py --uninstall
"""
import os
import subprocess
import sys

setup = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin", "setup.py")
sys.exit(subprocess.call([sys.executable, setup, "--manual", *sys.argv[1:]]))
