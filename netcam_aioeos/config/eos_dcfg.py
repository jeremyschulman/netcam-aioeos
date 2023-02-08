#  Copyright 2023 Jeremy Schulman
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

from typing import Optional

# =============================================================================
# This file contains the EOS "Device Under Test" class definition.  This is
# where the specific check-executors are wired into the class to support the
# various design-service checks.
# =============================================================================

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from aioeapi import Device as DeviceEAPI
from aioeapi.config_session import SessionConfig

from netcad.device import Device
from netcad.netcam.dev_config import AsyncDeviceConfigurable

# -----------------------------------------------------------------------------
# Privae Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_plugin_globals import g_eos

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------


class EOSDeviceConfigurable(AsyncDeviceConfigurable):
    """
    This class provides the Arista EOS device-under-test plugin for directly
    communicating with the device via the EAPI interface.  The underpinning
    transport is using asyncio.  Refer to the `aioeapi` distribution for further
    details.

    Attributes
    ----------
    eapi: aioeapi.Device
        The asyncio driver instance used to communicate with the EOS eAPI.
    """

    def __init__(self, *, device: Device, **_kwargs):
        """
        Initialize the instance with eAPI
        Parameters
        ----------
        device:
            The netcad device instance from the design.
        """
        super().__init__(device=device)
        self._scp_creds = g_eos.scp_creds
        self.eapi = DeviceEAPI(
            host=device.name, auth=g_eos.basic_auth_rw, timeout=g_eos.config.timeout
        )
        self.sesson_config: SessionConfig | None = None

    def _set_config_id(self, name: str):
        """
        The eAPI config session will be created when the Caller sets the
        config_id attribute.

        Parameters
        ----------
        name: str
            The name of the config session, which is the same as the config_id
            attribute.
        """
        self.sesson_config = self.eapi.config_session(name)

    async def check_reachability(self) -> bool:
        """
        Returns True when the device is reachable over eAPI, False otherwise.
        """
        return await self.eapi.check_connection()

    async def fetch_running_config(self) -> str:
        """
        Retrieves the current running configuration from the device.

        Returns
        -------
        The running config as a text string.
        """
        return await self.eapi.cli("show running-config", ofmt="text")

    async def load_config(self, config_contents: str, replace: Optional[bool] = False):
        """
        Attempts to load the given configuration into the session config.  If
        this fails for any reason an exception will be raised.

        Parameters
        ----------
        config_contents
        replace
        """
        await self.sesson_config.push(config_contents, replace=replace)

    async def abort_config(self):
        """Aborts the EOS session config"""
        await self.sesson_config.abort()

    async def diff_config(self) -> str:
        return await self.sesson_config.diff()
