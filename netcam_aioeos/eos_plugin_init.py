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

from os import environ
from pydantic import ValidationError
import httpx

from .eos_plugin_globals import g_eos
from .eos_plugin_config import EosPluginConfig


def plugin_init(plugin_def: dict):
    """
    This function is the required netcam plugin 'hook' that is called during the
    netcam tool initialization process.  The primary purpose of this function is
    to pass along the User defined configuration from the `netcad.toml` file.

    Parameters
    ----------
    plugin_def: dict
        The plugin definition as declared in the User `netcad.toml`
        configuration file.
    """

    if not (config := plugin_def.get("config")):
        return

    eos_plugin_config(config)


def eos_plugin_config(config: dict):
    """
    Called during plugin init, this function is used to setup the default
    credentials to access the EOS devices.

    Parameters
    ----------
    config: dict
        The dict object as defined in the User configuration file.
    """

    try:
        g_eos.config = EosPluginConfig.parse_obj(config)
    except ValidationError as exc:
        raise RuntimeError(f"invalid plugin configuration: {str(exc)}")

    try:
        g_eos.basic_auth = httpx.BasicAuth(
            username=environ[g_eos.config.env.username],
            password=environ[g_eos.config.env.password],
        )
    except KeyError as exc:
        raise RuntimeError(f"Missing environment variable: {exc.args[0]}")
