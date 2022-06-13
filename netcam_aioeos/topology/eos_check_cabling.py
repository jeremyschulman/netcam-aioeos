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
)
from netcad.topology.checks.utils_cabling_nei import (
    nei_interface_match,
    nei_hostname_match,
)

from netcad.device import Device
from netcad.netcam import any_failures
from netcad.checks import check_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_test_cabling", "eos_test_one_interface"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


@EOSDeviceUnderTest.execute_checks.register
async def eos_test_cabling(
    self, testcases: InterfaceCablingCheckCollection
) -> trt.CheckResultsCollection:
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
            results.append(trt.CheckFailNoExists(device=device, check=check))
            continue

        results.extend(
            eos_test_one_interface(
                device=dut.device,
                check=check,
                ifnei_status=port_nei,
            )
        )

    return results


def eos_test_one_interface(
    device: Device, check: InterfaceCablingCheck, ifnei_status: dict
) -> trt.CheckResultsCollection:
    """
    Validates the LLDP information for a specific interface.
    """
    results = list()

    expd_name = check.expected_results.device
    expd_port_id = check.expected_results.port_id

    msrd_name = ifnei_status["neighborDevice"]
    msrd_port_id = ifnei_status["neighborPort"]

    if not nei_hostname_match(expd_name, msrd_name):
        results.append(
            trt.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="device",
                measurement=msrd_name,
            )
        )

    if not nei_interface_match(expd_port_id, msrd_port_id):
        results.append(
            trt.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="port_id",
                measurement=msrd_port_id,
            )
        )

    if not any_failures(results):
        results.append(
            trt.CheckPassResult(device=device, check=check, measurement=ifnei_status)
        )

    return results
