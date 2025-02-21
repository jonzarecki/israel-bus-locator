import pytest
import os
import sys

# Add the parent directory to the Python path so we can import the module under test
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Any shared fixtures can be added here if needed in the future 