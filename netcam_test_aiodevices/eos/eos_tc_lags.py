# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, AsyncGenerator, Generator
from collections import defaultdict

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.testing_services.lags import LagTestCases, LagTestCase

from netcad.device import Device, DeviceInterface
from netcad.netcam import tc_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from netcam_test_aiodevices.eos import DeviceUnderTestEOS


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_test_lags", "eos_test_one_lag"]


async def eos_test_lags(self, testcases: LagTestCases) -> AsyncGenerator:

    dut: DeviceUnderTestEOS = self
    device = dut.device

    cli_lacp_resp = await dut.eapi.cli("show lacp interface")

    # The EOS data is a dictionary key is port-channel interface name.
    dev_lacp_data = cli_lacp_resp["portChannels"]

    for each_test in testcases.tests:

        # The test case ID is the port-channel interface name.
        if_name = each_test.test_case_id()

        # If the expected LAG does not exist raise that failure and continue
        # with the next interface.

        if not (lag_status := dev_lacp_data.get(if_name)):
            yield trt.FailNoExistsResult(device=device, test_case=each_test)
            continue

        for result in eos_test_one_lag(
            device=device, test_case=each_test, lag_status=lag_status
        ):
            yield result


def eos_test_one_lag(
    device: Device, test_case: LagTestCase, lag_status: dict
) -> Generator:

    fails = 0

    po_interfaces = lag_status["interfaces"]

    # -------------------------------------------------------------------------
    # check the interface bundle status.  we will use a defaultdict-list to find
    # any non-bundled values.
    # -------------------------------------------------------------------------

    bundle_status = defaultdict(list)
    for if_name, if_data in po_interfaces.items():
        bundle_status[if_data["actorPortStatus"]].append(if_name)

    bundle_status.pop("bundled")

    # if there are any keys remaining in the bundled_status dictionary this
    # means that there are interfaces in a non bundled state.  Need to report
    # this as a failure.

    if bundle_status:
        # TODO: yield an error
        fails += 1

    # -------------------------------------------------------------------------
    # Check for any missing or extra interfaces in the port-channel liss.
    # -------------------------------------------------------------------------

    msrd_interfaces = set(po_interfaces)

    expd_interfaces = set(
        lagif.interface for lagif in test_case.expected_results.interfaces
    )

    if missing_interfaces := expd_interfaces - msrd_interfaces:
        yield trt.FailMissingMembersResult(
            device=device,
            test_case=test_case,
            field="interfaces",
            expected=list(expd_interfaces),
            missing=list(missing_interfaces),
        )
        fails += 1

    if extra_interfaces := msrd_interfaces - expd_interfaces:
        yield trt.FailExtraMembersResult(
            device=device,
            test_case=test_case,
            field="interfaces",
            expected=list(expd_interfaces),
            extras=list(extra_interfaces),
        )
        fails += 1

    if fails:
        return

    # -------------------------------------------------------------------------
    # Test case passed
    # -------------------------------------------------------------------------

    if_list = [iface.name for iface in sorted(map(DeviceInterface, msrd_interfaces))]
    yield trt.PassTestCase(device=device, test_case=test_case, measurement=if_list)
