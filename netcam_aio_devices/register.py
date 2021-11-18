# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import List, Optional, Union
from pathlib import Path
import asyncio

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device
from netcad.testing_services.device_under_test import (
    DeviceUnderTest,
    AsyncDeviceUnderTest,
)

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

# from netcam_aio_devices.testing_services import SUPPORTED_TESTING_SERVICES
from netcam_aio_devices.eos import DeviceUnderTestEOS


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------

AnyDeviceUnderTest = Union[DeviceUnderTest, AsyncDeviceUnderTest]


SUPPORTED_OS_NAMES = {"eos": DeviceUnderTestEOS}


async def aio_execute_device_tests(
    dut: AsyncDeviceUnderTest, testcase_names: Optional[List[str]]
):
    pass


def execute_device_testing(dut: DeviceUnderTest, testcase_names: Optional[List[str]]):
    pass


def dispatch_device_tests(
    device: Device, testcases_dir: Path, testcases_names: Optional[List[str]] = None
):

    if not (dut_cls := SUPPORTED_OS_NAMES.get(device.os_name)):
        raise RuntimeError(
            f"Missing support for device: {device.name} os_name: {device.os_name}"
        )

    dut_obj: AnyDeviceUnderTest = dut_cls(device, testcases_dir=testcases_dir)

    if isinstance(dut_obj, AsyncDeviceUnderTest):
        asyncio.run(aio_execute_device_tests(dut_obj, testcases_names))
    else:
        execute_device_testing(dut_obj, testcases_names)
