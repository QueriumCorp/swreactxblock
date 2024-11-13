# -*- coding: utf-8 -*-
"""Note that importing SWPWRXBlock is a requirements of XBlock SDK."""

# pylint: disable=W0718,C0103
try:
    from .swpwrxblock import SWPWRXBlock  # noqa: F401
except Exception as e:
    description = str(e)
    print(f"swpwrxblock.__init__.py - ImportError: SWPWRXBlock {description}")
