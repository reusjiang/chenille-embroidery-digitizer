#!/usr/bin/env python3
"""Cross-platform entry for the Codex operator trial rulepack."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from chenille.operator_workflow import main

if __name__ == '__main__':
    raise SystemExit(main(ROOT))
