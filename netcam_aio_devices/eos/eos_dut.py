# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional
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

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["DeviceUnderTestEOS"]


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


class DeviceUnderTestEOS(AsyncDeviceUnderTest):
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
    async def execute_testcases(self, testcases: TestCases):
        """dispatch the testcases to the registered methods"""
        cls_name = testcases.__class__.__name__
        raise RuntimeError(
            f'Missing: device {self.device.name} support for testcases of type "{cls_name}"'
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
