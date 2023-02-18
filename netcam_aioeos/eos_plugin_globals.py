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

from typing import Optional, Tuple

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import httpx

from dataclasses import dataclass
from .eos_plugin_config import EosPluginConfig


@dataclass
class EosGlobals:
    """
    Define a class to encapsulate the global variables used by this plugin.

    Attributes
    ----------
    basic_auth: httpx.BasicAuth
        The authorization value that will be used for read-only access the EOS
        devices via eAPI. This username-password auth combination is prepared
        once during initialization so that we do not need to duplicate the
        calls for each DUT.

        Note that this approach does (currently) preclude the use of
        per-device authorizations.  TODO: feature.

    basic_auth_rw: httpx.BasicAuth
        The authorization used for read-write access.  This is used primarily
        for configuration management.

    config: dict
        This is the plugin configuration dictionary as declared in the User
        `netcad.toml` configuration file.
    """

    basic_auth: Optional[httpx.BasicAuth] = None
    basic_auth_rw: Optional[httpx.BasicAuth] = None
    config: Optional[EosPluginConfig] = None
    scp_creds: Optional[Tuple[str, str]] = None


# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------

# the global variables used by this plugin
g_eos = EosGlobals()
