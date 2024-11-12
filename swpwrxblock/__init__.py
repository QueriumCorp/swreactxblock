# -*- coding: utf-8 -*-
"""Note that importing SWPWRXBlock is a requirements of XBlock SDK."""

try:
    from .swpwrxblock import SWPWRXBlock  # noqa: F401
except (ImportError, ModuleNotFoundError):
    print("swpwrxblock.__init__.py - ImportError: SWPWRXBlock")
