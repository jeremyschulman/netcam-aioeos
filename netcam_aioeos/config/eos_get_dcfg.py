#  Copyright 2023 Jeremy Schulman
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
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.config.eos_dcfg import EOSDeviceConfigurable

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["plugin_get_dcfg"]

# -----------------------------------------------------------------------------
#
#                            CODE BEGINS
#
# -----------------------------------------------------------------------------


def plugin_get_dcfg(device: Device) -> EOSDeviceConfigurable:
    """
    This function is the required netcam plugin hook that allows the netcam
    tool to obtain the device-configurable instance for a specific device.  The
    device instance MUST* have the os_name attribute set to "eos".

    Parameters
    ----------
    device: Device
        The device instance used to originate the DUT instance.

    Raises
    ------
    RuntimeError
        When the device instance is not os_name=="eos"

    Returns
    -------
    The EOS device-under-test instance used for operational checking.
    """

    if device.os_name != "eos":
        raise RuntimeError(
            f"Missing required DCFG class for device {device.name}, os_name: {device.os_name}"
        )

    return EOSDeviceConfigurable(device=device)
