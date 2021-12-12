# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.topology.tc_cabling_nei import (
    InterfaceCablingTestCases,
    InterfaceCablingTestCase,
)
from netcad.topology.utils_cabling_nei import (
    nei_interface_match,
    nei_hostname_match,
)

from netcad.device import Device
from netcad.netcam import tc_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from netcam_test_aiodevices.eos import EOSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_test_cabling", "eos_test_one_interface"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def eos_test_cabling(
    self, testcases: InterfaceCablingTestCases
) -> trt.CollectionTestResults:
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

    for test_case in testcases.tests:
        if_name = test_case.test_case_id()

        if not (port_nei := dev_lldpnei_ifname.get(if_name)):
            results.append(trt.FailNoExistsResult(device=device, test_case=test_case))
            continue

        results.extend(
            eos_test_one_interface(
                device=dut.device,
                test_case=test_case,
                ifnei_status=port_nei,
            )
        )

    return results


def eos_test_one_interface(
    device: Device, test_case: InterfaceCablingTestCase, ifnei_status: dict
) -> trt.CollectionTestResults:

    results = list()

    expd_name = test_case.expected_results.device
    expd_port_id = test_case.expected_results.port_id

    msrd_name = ifnei_status["neighborDevice"]
    msrd_port_id = ifnei_status["neighborPort"]

    if not nei_hostname_match(expd_name, msrd_name):
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="device",
                measurement=msrd_name,
            )
        )

    if not nei_interface_match(expd_port_id, msrd_port_id):
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="port_id",
                measurement=msrd_port_id,
            )
        )

    if not any(isinstance(res, trt.FailTestCase) for res in results):
        results.append(
            trt.PassTestCase(
                device=device, test_case=test_case, measurement=ifnei_status
            )
        )

    return results
