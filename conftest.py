"""
Ensures the project root is on sys.path so tests can `import tools` and
`import agent` regardless of how pytest is invoked (`pytest` or `python -m pytest`).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
