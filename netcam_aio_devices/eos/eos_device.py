# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from aioeapi import Device as EapiDevice

from netcad.device import Device
from netcad.testing_services.device_under_test import AsyncDeviceUnderTest


__all__ = ["DeviceUnderTestEOS"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


class DeviceUnderTestEOS(AsyncDeviceUnderTest):
    def __init__(self, device: Device, **kwargs):
        super().__init__(device=device, **kwargs)
        self._eos = EapiDevice(host=device.name)

    async def setup(self):
        await self._eos.cli("show version")

    async def teardown(self):
        await self._eos.aclose()
