# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from pathlib import Path

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos import EOSDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["plugin_get_dut"]

# -----------------------------------------------------------------------------
#
#                            CODE BEGINS
#
# -----------------------------------------------------------------------------


def plugin_get_dut(device: Device, testcases_dir: Path):

    if device.os_name != "eos":
        raise RuntimeError(
            f"Missing required DUT class for device {device.name}, os_name: {device.os_name}"
        )

    return EOSDeviceUnderTest(device=device, testcases_dir=testcases_dir)
