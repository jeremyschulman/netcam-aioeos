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

# =============================================================================
# This file contains the EOS "Device Under Test" class definition.  This is
# where the specific check-executors are wired into the class to support the
# various design-service checks.
# =============================================================================

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

import asyncio
from typing import Optional
from functools import singledispatchmethod

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

    Attributes
    ----------
    eapi: aioeapi.Device
        The asyncio driver instance used to communicate with the EOS eAPI.

    version_info: dict
        The results of 'show version' that is extracted from the device during
        the `setup` process.
    """

    def __init__(self, *, device: Device, **_kwargs):
        """DUT construction creates instance of EAPI transport"""

        super().__init__(device=device)
        self.eapi = DeviceEAPI(host=device.name, auth=g_eos.basic_auth)
        self.version_info: Optional[dict] = None

        # inialize the DUT cache mechanism; used exclusvely by the
        # `api_cache_get` method.

        self._api_cache_lock = asyncio.Lock()
        self._api_cache = dict()

    # -------------------------------------------------------------------------
    #
    #                       EOS DUT Specific Methods
    #
    # -------------------------------------------------------------------------

    async def api_cache_get(self, key: str, command: str, **kwargs):
        """
        This function is used by other class methods that want to abstract the
        collection function of a given eAPI routine so that the results of that
        call are cached and avaialble for other check executors.  This method
        should not be called outside other methods of this DUT class, but this
        is not a hard constraint.

        For example, if the result of "show interface switchport" is going to be
        used by multiple check executors, then there would exist a method in
        this class called `get_switchports` that uses this `api_cache_get`
        method.

        Parameters
        ----------
        key: str
            The cache-key string that is used to uniquely identify the contents
            of the cache.  For example 'switchports' may be the cache key to cache
            the results of the 'show interfaces switchport' command.

        command: str
            The actual EOS CLI command used to obtain the eAPI results.

        Other Parameters
        ----------------
        Any keyword-args supported by the underlying eAPI Device driver; for
        example `ofmt` can be used to change the output format from the default
        of dict to text.  Refer to the aio-eapi package for further details.

        Returns
        -------
        Either the cached data corresponding to the key if exists in the cache,
        or the newly retrieved data from the device; which is then cached for
        future use.
        """
        async with self._api_cache_lock:
            if not (has_data := self._api_cache.get(key)):
                has_data = await self.eapi.cli(command, **kwargs)
                self._api_cache[key] = has_data

            return has_data

    async def get_switchports(self) -> dict:
        """
        Return the device operational status of interface switchports.
        """
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
    async def execute_checks(
        self, checks: CheckCollection
    ) -> Optional[CheckResultsCollection]:
        """
        This method is only called when the DUT does not support a specific
        design-service check.  This function *MUST* exist so that the supported
        checks can be "wired into" this class using the dispatch register mechanism.
        """
        return super().execute_checks()

    # -------------------------------------------------------------------------
    #
    #                          DUT Check Executors
    #
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Support the 'topology device' check
    # -------------------------------------------------------------------------

    from netcam_aioeos.topology.eos_check_device_info import eos_check_device_info

    execute_checks.register(eos_check_device_info)

    # -------------------------------------------------------------------------
    # Support the 'topology interfaces' checks
    # -------------------------------------------------------------------------

    from netcam_aioeos.topology.eos_check_interfaces import eos_check_interfaces

    execute_checks.register(eos_check_interfaces)

    # -------------------------------------------------------------------------
    # Support the 'topology transceivers' checks
    # -------------------------------------------------------------------------

    from netcam_aioeos.topology.eos_check_transceivers import eos_check_transceivers

    execute_checks.register(eos_check_transceivers)

    # -------------------------------------------------------------------------
    # Support the 'topology cabling' checks
    # -------------------------------------------------------------------------

    from netcam_aioeos.topology.eos_check_cabling import eos_test_cabling

    execute_checks.register(eos_test_cabling)

    # -------------------------------------------------------------------------
    # Support the 'vlans vlans' checks
    # -------------------------------------------------------------------------

    from netcam_aioeos.vlans.eos_check_vlans import eos_check_vlans

    execute_checks.register(eos_check_vlans)

    # -------------------------------------------------------------------------
    # Support the 'topology lags' checks
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
    # Support the 'topology ipaddrs' checks
    # -------------------------------------------------------------------------

    from netcam_aioeos.topology.eos_check_ipaddrs import eos_test_ipaddrs

    execute_checks.register(eos_test_ipaddrs)

    # -------------------------------------------------------------------------
    # Support the 'vlan switchports' checks
    # -------------------------------------------------------------------------

    from netcam_aioeos.vlans.eos_check_switchports import eos_check_switchports

    execute_checks.register(eos_check_switchports)
