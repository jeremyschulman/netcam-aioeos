# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from functools import singledispatchmethod

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

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


class DeviceUnderTestEOS(AsyncDeviceUnderTest):
    def __init__(self, device: Device, **_kwargs):
        super().__init__(device=device)
        self.eapi = DeviceEAPI(host=device.name)

    async def setup(self):
        await self.eapi.cli("show version")

    async def teardown(self):
        await self.eapi.aclose()

    @singledispatchmethod
    async def execute_testcases(self, testcases: TestCases):
        cls_name = testcases.__class__.__name__
        raise RuntimeError(
            f'Missing: device {self.device.name} support for testcases of type "{cls_name}"'
        )

    from .eos_tc_device_info import eos_tc_device_info

    execute_testcases.register(eos_tc_device_info)

    from .eos_tc_interfaces import eos_tc_interfaces

    execute_testcases.register(eos_tc_interfaces)
