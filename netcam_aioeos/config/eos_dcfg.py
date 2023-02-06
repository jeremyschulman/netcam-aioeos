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

# =============================================================================
# This file contains the EOS "Device Under Test" class definition.  This is
# where the specific check-executors are wired into the class to support the
# various design-service checks.
# =============================================================================


# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from aioeapi import Device as DeviceEAPI
from netcad.device import Device
from netcad.netcam.dev_config import AsyncDeviceConfigurable

# -----------------------------------------------------------------------------
# Privae Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_plugin_config import g_eos

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
        self.eapi = DeviceEAPI(
            host=device.name, auth=g_eos.basic_auth, timeout=g_eos.config.timeout
        )

    async def fetch_running_config(self) -> str:
        """
        Retrieves the current running configuration from the device.

        Returns
        -------
        The running config as a text string.
        """
        return await self.eapi.cli("show running-config", ofmt="text")
