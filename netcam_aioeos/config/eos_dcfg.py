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

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from aioeapi import Device as DeviceEAPI
from aioeapi.config_session import SessionConfig

from netcad.device import Device
from netcam.dcfg import AsyncDeviceConfigurable

# -----------------------------------------------------------------------------
# Privae Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_plugin_globals import g_eos

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

_Caps = AsyncDeviceConfigurable.Capabilities


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

    DEFAULT_CAPABILITIES = _Caps.diff | _Caps.rollback | _Caps.check | _Caps.replace

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
        self._dev_fs = "flash:"
        self.eapi = DeviceEAPI(
            host=device.name, auth=g_eos.basic_auth_rw, timeout=g_eos.config.timeout
        )
        self.sesson_config: SessionConfig | None = None
        self.capabilities = self.DEFAULT_CAPABILITIES

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

    @property
    def local_file(self):
        return f"flash:{self.config_file.name}"

    async def is_reachable(self) -> bool:
        """
        Returns True when the device is reachable over eAPI, False otherwise.
        """
        return await self.eapi.check_connection()

    async def config_get(self) -> str:
        """
        Retrieves the current running configuration from the device.

        Returns
        -------
        The running config as a text string.
        """
        return await self.eapi.cli("show running-config", ofmt="text")

    async def config_cancel(self):
        """Aborts the EOS session config"""
        await self.sesson_config.abort()

    async def config_check(self, replace: Optional[bool | None] = None) -> str | None:
        try:
            await self.sesson_config.load_scp_file(
                filename=self.local_file, replace=replace or self.replace
            )
        except RuntimeError as exc:
            errors = exc.args[0]
        else:
            errors = None

        self.config_diff_contents = await self.sesson_config.diff()
        await self.sesson_config.abort()

        return errors

    async def config_diff(self) -> str:
        self.config_diff_contents = await self.sesson_config.diff()
        return self.config_diff_contents

    async def config_replace(self, rollback_timeout: int):
        """ """
        await self.sesson_config.load_scp_file(filename=self.local_file, replace=True)

        # capture the diffs before running the commit
        self.config_diff_contents = await self.sesson_config.diff()

        # if there are no diffs, abort the session, and return
        if not self.config_diff_contents:
            await self.sesson_config.abort()
            return

        await self.sesson_config.commit(timer=f"00:{rollback_timeout:02}:00")

        if not await self.is_reachable():
            raise RuntimeError(f"{self.device.name}: device is no longer reachable.")

        # commit the configuration and copy running to startup
        await self.sesson_config.commit()
        await self.eapi.cli("write")

    async def file_delete(self):
        """
        This function is used to remove the configuration file that was
        previously copied to the remote device.  This function is expected to
        be called during a "cleanup" process.
        """
        await self.eapi.cli(f"delete {self.local_file}")

    async def config_merge(self, rollback_timeout: int):
        raise RuntimeError(
            f"{self.device.name}: EOS config-mgmt does not support merge"
        )
