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

from typing import Optional
from os import environ

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import httpx
from pydantic import BaseModel, Field, Extra, ValidationError

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["init_config", "g_eos"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------

DEFAULT_ENV_USERNAME = "NETWORK_USERNAME"
DEFAULT_ENV_PASSWORD = "NETWORK_PASSWORD"

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------


class EosGlobals:
    """
    Define a class to encapsulate the global variables used by this plugin.

    Attributes
    ----------
    basic_auth: httpx.BasicAuth
        The authorization value that will be used to access the EOS devices via
        eAPI. This username-password auth combination is prepared once during
        initialization so that we do not need to duplicate the calls for each
        DUT.  Note that this approach does (currently) preclude the use of
        per-device authorizations.  TODO: feature.

    config: dict
        This is the plugin configuration dictionary as declared in the User
        `netcad.toml` configuration file.
    """

    def __init__(self):
        """
        Init globals to None.  These values will be setup during the plugin_init
        invocation.
        """
        self.basic_auth: Optional[httpx.BasicAuth] = None
        self.config: Optional[EosConfig] = None


# the global variables used by this plugin
g_eos = EosGlobals()


# -----------------------------------------------------------------------------
# Use pydantic models to validate the User configuration file.  Configure
# pydantic to prevent the User from providing (accidentally) any fields that are
# not specifically supported; via the Extra.forbid config.
# -----------------------------------------------------------------------------


class EosEnvConfig(BaseModel, extra=Extra.forbid):
    """
    Define the environment variable names to source the username and password values.  When
    provided, these will override the default values.
    """

    username: str = Field(default=DEFAULT_ENV_USERNAME)
    password: str = Field(default=DEFAULT_ENV_PASSWORD)


class EosConfig(BaseModel, extra=Extra.forbid):
    """define the schema for the plugin configuration"""

    env: EosEnvConfig


def init_config(config: dict):
    """
    Called during plugin init, this function is used to setup the default
    credentials to access the EOS devices.

    Parameters
    ----------
    config: dict
        The dict object as defined in the User configuration file.
    """

    try:
        g_eos.config = EosConfig.parse_obj(config)
    except ValidationError as exc:
        raise RuntimeError(f"invalid plugin configuration: {str(exc)}")

    try:
        g_eos.basic_auth = httpx.BasicAuth(
            username=environ[g_eos.config.env.username],
            password=environ[g_eos.config.env.password],
        )
    except KeyError as exc:
        raise RuntimeError(f"Missing environment variable: {exc.args[0]}")
