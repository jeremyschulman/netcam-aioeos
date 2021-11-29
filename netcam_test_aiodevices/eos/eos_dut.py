# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional, AsyncGenerator
import os
from functools import singledispatchmethod

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------
import httpx
from aioeapi import Device as DeviceEAPI

from netcad.device import Device
from netcad.testing_services import TestCases
from netcad.netcam.dut import AsyncDeviceUnderTest
from netcad.netcam import SkipTestCases

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

    def __init__(self, device: Device, **_kwargs):
        """DUT construction creates instance of EAPI transport"""
        super().__init__(device=device)
        self.eapi = DeviceEAPIAuth(host=device.name)
        self.version_info: Optional[dict] = None

    async def setup(self):
        """DUT setup process"""
        self.version_info = await self.eapi.cli("show version")

    async def teardown(self):
        """DUT tearndown process"""
        await self.eapi.aclose()

    @singledispatchmethod
    async def execute_testcases(self, testcases: TestCases) -> AsyncGenerator:
        """dispatch the testcases to the registered methods"""
        cls_name = testcases.__class__.__name__

        yield SkipTestCases(
            device=self.device,
            test_case=testcases.tests[0],
            message=f'Missing: device {self.device.name} support for testcases of type "{cls_name}"',
        )

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

    from .eos_tc_lags import eos_test_lags

    execute_testcases.register(eos_test_lags)

    # -------------------------------------------------------------------------
    # Support the 'mlags' testcases
    # -------------------------------------------------------------------------

    from .eos_tc_mlags import eos_test_mlags

    execute_testcases.register(eos_test_mlags)
