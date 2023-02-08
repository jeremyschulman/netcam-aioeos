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
        raise RuntimeError(f"Failed to load EOS plugin configuration: {str(exc)}")

    g_eos.basic_auth = httpx.BasicAuth(
        username=g_eos.config.env.read.username.get_secret_value(),
        password=g_eos.config.env.read.password.get_secret_value(),
    )

    # If the User provides the admin credential environment variobles, then set
    # up the admin authentication that is used for configruation management

    if admin := g_eos.config.env.admin:
        admin_user = admin.username.get_secret_value()
        adin_passwd = admin.password.get_secret_value()
        g_eos.basic_auth_rw = httpx.BasicAuth(admin_user, adin_passwd)
        g_eos.scp_creds = (admin_user, adin_passwd)
