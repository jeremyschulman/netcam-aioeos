# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, AsyncGenerator, Generator

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.testing_services.cabling import (
    InterfaceCablingTestCases,
    InterfaceCablingTestCase,
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
) -> AsyncGenerator:
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

    cli_lldp_rsp = await dut.eapi.cli("show lldp neighbors")

    # create a map of local interface name to the LLDP neighbor record.

    dev_lldpnei_ifname = {nei["port"]: nei for nei in cli_lldp_rsp["lldpNeighbors"]}

    for each_test in testcases.tests:
        if_name = each_test.test_case_id()

        for result in eos_test_one_interface(
            device=dut.device,
            test_case=each_test,
            ifnei_status=dev_lldpnei_ifname.get(if_name),
        ):
            yield result


def eos_test_one_interface(
    device: Device, test_case: InterfaceCablingTestCase, ifnei_status: dict
) -> Generator:
    """
    Perform the actual tests for one interface.

    Parameters
    ----------
    device:
        Netcad Device instance

    test_case:
        The specific interface test-case

    ifnei_status:
        The actual LLDP neighbor data from the EOS device.

    Yields
    ------
    Netcad test-case results
    """

    if not ifnei_status:
        yield trt.FailNoExistsResult(device=device, test_case=test_case)
        return

    fails = 0

    expd_name = test_case.expected_results.device
    expd_ifname = test_case.expected_results.interface

    msrd_name = ifnei_status["neighborDevice"]
    msrd_ifname = ifnei_status["neighborPort"]

    if not nei_hostname_match(expd_name, msrd_name):
        yield trt.FailFieldMismatchResult(
            device=device, test_case=test_case, field="device", measurement=msrd_name
        )
        fails += 1

    if not nei_interface_match(expd_ifname, msrd_ifname):
        yield trt.FailFieldMismatchResult(
            device=device, test_case=test_case, field="interface", measurement=msrd_name
        )
        fails += 1

    if fails:
        return

    # -------------------------------------------------------------------------
    # No failures, so test passes
    # -------------------------------------------------------------------------

    yield trt.PassTestCase(device=device, test_case=test_case, measurement=ifnei_status)
