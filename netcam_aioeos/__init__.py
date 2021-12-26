#  Copyright 2021 Jeremy Schulman
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

import importlib.metadata as importlib_metadata

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from .eos_get_dut import plugin_get_dut
from .eos_init import plugin_init

plugin_version = importlib_metadata.version(__name__)
plugin_description = "NetCadCam plugin for Arista EOS systems (asyncio)"
