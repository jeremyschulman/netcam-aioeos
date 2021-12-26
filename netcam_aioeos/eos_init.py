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

from .eos_config import init_config


def plugin_init(config: dict):
    """
    This function is the required netcam plugin 'hook' that is called during the
    netcam tool initialization process.  The primary purpose of this function is
    to pass along the User defined configuration from the `netcad.toml` file.

    Parameters
    ----------
    config: dict
        The configuration for this plugin as declared in the User `netcad.toml`
        configuration file.
    """
    if not config:
        return

    init_config(config)
