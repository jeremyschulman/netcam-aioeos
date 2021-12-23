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
    def __init__(self):
        self.basic_auth: Optional[httpx.BasicAuth] = None
        self.config: Optional[EosConfig] = None


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
