# -*- coding: utf-8 -*-
import os
import sys

os.environ.setdefault("PYTHONUTF8", "1")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app.main import main

if __name__ == "__main__":
    main()
