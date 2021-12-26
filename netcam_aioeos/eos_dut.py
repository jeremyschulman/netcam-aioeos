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

import asyncio
from typing import Optional
from functools import singledispatchmethod
from pathlib import Path

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import httpx
from aioeapi import Device as DeviceEAPI

from netcad.device import Device
from netcad.checks import CheckCollection
from netcad.netcam.dut import AsyncDeviceUnderTest
from netcad.netcam import CheckResultsCollection

# -----------------------------------------------------------------------------
# Privae Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_config import g_eos

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["EOSDeviceUnderTest"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


class EOSDeviceUnderTest(AsyncDeviceUnderTest):
    """
    This class provides the Arista EOS device-under-test plugin for directly
    communicating with the device via the EAPI interface.  The underpinning
    transport is using asyncio.  Refer to the `aioeapi` distribution for further
    details.
    """

    def __init__(self, *, device: Device, testcases_dir: Path, **_kwargs):
        """DUT construction creates instance of EAPI transport"""

        super().__init__(device=device, testcases_dir=testcases_dir)
        self.eapi = DeviceEAPI(host=device.name, auth=g_eos.basic_auth)
        self.version_info: Optional[dict] = None
        self._api_cache_lock = asyncio.Lock()
        self._api_cache = dict()

    # -------------------------------------------------------------------------
    #
    #                       EOS DUT Specific Methods
    #
    # -------------------------------------------------------------------------

    async def api_cache_get(self, key: str, command: str, **kwargs):
        async with self._api_cache_lock:
            if not (has_data := self._api_cache.get(key)):
                has_data = await self.eapi.cli(command, **kwargs)
                self._api_cache[key] = has_data

            return has_data

    async def get_switchports(self):
        return await self.api_cache_get(
            key="switchports", command="show interfaces switchport"
        )

    # -------------------------------------------------------------------------
    #
    #                              DUT Methods
    #
    # -------------------------------------------------------------------------

    async def setup(self):
        """DUT setup process"""
        await super().setup()

        if not await self.eapi.check_connection():
            raise RuntimeError(
                f"Unable to connect to EOS device: {self.device.name}: "
                "Device offline or eAPI is not enabled, check config."
            )

        try:
            self.version_info = await self.eapi.cli("show version")

        except httpx.HTTPError as exc:
            rt_exc = RuntimeError(
                f"Unable to connect to EOS device {self.device.name}: {str(exc)}"
            )
            rt_exc.__traceback__ = exc.__traceback__
            await self.teardown()
            raise rt_exc

    async def teardown(self):
        """DUT tearndown process"""
        await self.eapi.aclose()

    @singledispatchmethod
    async def execute_testcases(
        self, testcases: CheckCollection
    ) -> Optional[CheckResultsCollection]:
        return None

    # -------------------------------------------------------------------------
    #
    #                          DUT Testcase Executors
    #
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Support the 'device' testcases
    # -------------------------------------------------------------------------

    from netcam_aioeos.topology.eos_check_device_info import eos_tc_device_info

    execute_testcases.register(eos_tc_device_info)

    # -------------------------------------------------------------------------
    # Support the 'interfaces' testcases
    # -------------------------------------------------------------------------

    from netcam_aioeos.topology.eos_check_interfaces import eos_tc_interfaces

    execute_testcases.register(eos_tc_interfaces)

    # -------------------------------------------------------------------------
    # Support the 'transceivers' testcases
    # -------------------------------------------------------------------------

    from netcam_aioeos.topology.eos_check_transceivers import eos_test_transceivers

    execute_testcases.register(eos_test_transceivers)

    # -------------------------------------------------------------------------
    # Support the 'cabling' testcases
    # -------------------------------------------------------------------------

    from netcam_aioeos.topology.eos_check_cabling import eos_test_cabling

    execute_testcases.register(eos_test_cabling)

    # -------------------------------------------------------------------------
    # Support the 'vlans' testcases
    # -------------------------------------------------------------------------

    from netcam_aioeos.vlans.eos_check_vlans import eos_check_vlans

    execute_testcases.register(eos_check_vlans)

    # -------------------------------------------------------------------------
    # Support the 'lags' testcases
    # -------------------------------------------------------------------------

    # from .eos_tc_lags import eos_test_lags
    #
    # execute_testcases.register(eos_test_lags)

    # -------------------------------------------------------------------------
    # Support the 'mlags' testcases
    # -------------------------------------------------------------------------

    # from .eos_tc_mlags import eos_test_mlags
    #
    # execute_testcases.register(eos_test_mlags)

    # -------------------------------------------------------------------------
    # Support the 'ipaddrs' testcases
    # -------------------------------------------------------------------------

    from netcam_aioeos.topology.eos_check_ipaddrs import eos_test_ipaddrs

    execute_testcases.register(eos_test_ipaddrs)

    # -------------------------------------------------------------------------
    # Support the 'switchports' testcases
    # -------------------------------------------------------------------------

    from netcam_aioeos.vlans.eos_check_switchports import eos_tc_switchports

    execute_testcases.register(eos_tc_switchports)
