"""
Shared test setup. Adds the project root to sys.path so `app.*` and `main`
can be imported when tests are run from the repository root or the tests
directory.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
