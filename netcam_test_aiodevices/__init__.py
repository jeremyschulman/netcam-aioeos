# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

import importlib.metadata as importlib_metadata
from pathlib import Path

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_test_aiodevices.eos import EOSDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["__version__", "get_dut"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------

__version__ = importlib_metadata.version(__name__)

SUPPORTED_OS_NAMES = {"eos": EOSDeviceUnderTest}


def get_dut(device: Device, testcases_dir: Path):

    if not (dut_cls := SUPPORTED_OS_NAMES.get(device.os_name)):
        raise RuntimeError(
            f"Missing required DUT class for device {device.name}, os_name: {device.os_name}"
        )

    return dut_cls(device=device, testcases_dir=testcases_dir)
