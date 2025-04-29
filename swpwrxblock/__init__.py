# -*- coding: utf-8 -*-
"""Note that importing SWREACTXBlock is a requirements of XBlock SDK."""

# pylint: disable=W0718,C0103
try:
    from .swreactxblock import SWREACTXBlock  # noqa: F401
except Exception as e:
    description = str(e)
    print(
        f"swreactxblock.__init__.py - Warning: encountered the following exception when attempting to import SWREACTXBlock {description}. You can ignore this warning during pip installation."
    )
