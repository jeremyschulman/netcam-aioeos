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

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from pydantic import BaseModel, Extra
from pydantic_env.models import EnvSecretStr

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["EosPluginConfig"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Use pydantic models to validate the User configuration file.  Configure
# pydantic to prevent the User from providing (accidentally) any fields that are
# not specifically supported; via the Extra.forbid config.
# -----------------------------------------------------------------------------


class EosPluginEnvCreds(BaseModel, extra=Extra.forbid):
    """
    Define the environment variable names to source the username and password values.  When
    provided, these will override the default values.

    The read-write (rw) values are used for configuration management.  The User
    environment may not need these features, and therefore these config
    parameters are optional.
    """

    username: EnvSecretStr
    password: EnvSecretStr


class EosPluginEnvConfig(BaseModel, extra=Extra.forbid):
    read: EosPluginEnvCreds
    admin: Optional[EosPluginEnvCreds] = None


class EosPluginConfig(BaseModel, extra=Extra.forbid):
    """define the schema for the plugin configuration"""

    env: EosPluginEnvConfig
    timeout: int = 60
