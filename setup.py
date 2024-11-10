# -*- coding: utf-8 -*-
# Pylint: disable=W0718,W0611,W1203
"""Setup for swpwrxblock XBlock."""

import os
from copy_assets import copy_assets

ENVIRONMENT_ID = os.environ.get("ENVIRONMENT_ID", "prod")
copy_assets(ENVIRONMENT_ID)
