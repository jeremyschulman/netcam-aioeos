# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------
import asyncio
from typing import Optional
import os
from functools import singledispatchmethod
from pathlib import Path

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import httpx
from aioeapi import Device as DeviceEAPI

from netcad.device import Device
from netcad.testing_services import TestCases
from netcad.netcam.dut import AsyncDeviceUnderTest
from netcad.netcam import CollectionTestResults

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["EOSDeviceUnderTest"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


class DeviceEAPIAuth(DeviceEAPI):
    """define a class that uses environment variables for EAPI auth acccess."""

    auth = httpx.BasicAuth(
        username=os.environ["NETWORK_USERNAME"], password=os.environ["NETWORK_PASSWORD"]
    )


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
        self.eapi = DeviceEAPIAuth(host=device.name)
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
        self.version_info = await self.eapi.cli("show version")

    async def teardown(self):
        """DUT tearndown process"""
        await self.eapi.aclose()

    @singledispatchmethod
    async def execute_testcases(
        self, testcases: TestCases
    ) -> Optional[CollectionTestResults]:
        return None

    # -------------------------------------------------------------------------
    #
    #                          DUT Testcase Executors
    #
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Support the 'device' testcases
    # -------------------------------------------------------------------------

    from .eos_tc_device_info import eos_tc_device_info

    execute_testcases.register(eos_tc_device_info)

    # -------------------------------------------------------------------------
    # Support the 'interfaces' testcases
    # -------------------------------------------------------------------------

    from .eos_tc_interfaces import eos_tc_interfaces

    execute_testcases.register(eos_tc_interfaces)

    # -------------------------------------------------------------------------
    # Support the 'transceivers' testcases
    # -------------------------------------------------------------------------

    from .eos_tc_transceivers import eos_test_transceivers

    execute_testcases.register(eos_test_transceivers)

    # -------------------------------------------------------------------------
    # Support the 'cabling' testcases
    # -------------------------------------------------------------------------

    from .eos_tc_cabling import eos_test_cabling

    execute_testcases.register(eos_test_cabling)

    # -------------------------------------------------------------------------
    # Support the 'vlans' testcases
    # -------------------------------------------------------------------------

    from .eos_tc_vlans import eos_test_vlans

    execute_testcases.register(eos_test_vlans)

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

    from .eos_tc_ipaddrs import eos_test_ipaddrs

    execute_testcases.register(eos_test_ipaddrs)

    # -------------------------------------------------------------------------
    # Support the 'switchports' testcases
    # -------------------------------------------------------------------------

    from .eos_tc_switchports import eos_tc_switchports

    execute_testcases.register(eos_tc_switchports)
