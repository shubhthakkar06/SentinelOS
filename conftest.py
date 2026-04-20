import sys
import os

# Add the project root to sys.path so `sentinel_os` is importable
# without installing the package. This is the standard pytest approach.
sys.path.insert(0, os.path.dirname(__file__))
