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
#

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.topology.checks.check_cabling_nei import (
    InterfaceCablingCheckCollection,
    InterfaceCablingCheck,
    InterfaceCablingCheckResult,
)
from netcad.topology.checks.utils_cabling_nei import (
    nei_interface_match,
    nei_hostname_match,
)

from netcad.device import Device
from netcad.checks import CheckResultsCollection, CheckStatus

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = []

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


@EOSDeviceUnderTest.execute_checks.register  # noqa
async def eos_check_cabling(
    self, testcases: InterfaceCablingCheckCollection
) -> CheckResultsCollection:
    """
    Support the "cabling" tests for Arista EOS devices.  These tests are
    implementeding by examing the LLDP neighborship status.

    This function is imported directly into the EOS DUT class defintion.

    Parameters
    ----------
    self: ** DO NOT TYPE HINT **
        EOS DUT instance

    testcases:
        The device specific cabling testcases as build via netcad.

    Yields
    ------
    Netcad test-case items.
    """
    dut: EOSDeviceUnderTest = self
    device = dut.device
    results = list()

    cli_lldp_rsp = await dut.eapi.cli("show lldp neighbors")

    # create a map of local interface name to the LLDP neighbor record.

    dev_lldpnei_ifname = {nei["port"]: nei for nei in cli_lldp_rsp["lldpNeighbors"]}

    for check in testcases.checks:
        if_name = check.check_id()

        if not (port_nei := dev_lldpnei_ifname.get(if_name)):
            result = InterfaceCablingCheckResult(
                device=device, check=check, measurement=None
            )
            results.append(result.measure())
            continue

        _check_one_interface(
            device=dut.device, check=check, ifnei_status=port_nei, results=results
        )

    return results


def _check_one_interface(
    device: Device,
    check: InterfaceCablingCheck,
    ifnei_status: dict,
    results: CheckResultsCollection,
):
    """
    Validates the LLDP information for a specific interface.
    """
    result = InterfaceCablingCheckResult(device=device, check=check)
    msrd = result.measurement

    msrd.device = ifnei_status["neighborDevice"]
    msrd.port_id = ifnei_status["neighborPort"]

    def on_mismatch(_field, _expd, _msrd):
        is_ok = False
        match _field:
            case "device":
                is_ok = nei_hostname_match(_expd, _msrd)
            case "port_id":
                is_ok = nei_interface_match(_expd, _msrd)

        return CheckStatus.PASS if is_ok else CheckStatus.FAIL

    results.append(result.measure(on_mismatch=on_mismatch))
