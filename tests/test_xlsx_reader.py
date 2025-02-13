"""
This file is kept for backward compatibility.
The tests have been reorganized into:
- test_xlsx_reader_unit.py: Unit tests with mocks
- test_xlsx_reader_integration.py: Integration tests with real files
- test_xlsx_reader_validation.py: Data validation tests
"""

from test_xlsx_reader_unit import *
from test_xlsx_reader_integration import *
from test_xlsx_reader_validation import *