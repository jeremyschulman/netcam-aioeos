# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING, AsyncGenerator, Generator

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.testing_services.vlans import VlanTestCases, VlanTestCase

from netcad.device import Device
from netcad.netcam import tc_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from netcam_test_aiodevices.eos import DeviceUnderTestEOS


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_test_vlans"]


async def eos_test_vlans(self, testcases: VlanTestCases) -> AsyncGenerator:

    dut: DeviceUnderTestEOS = self
    device = dut.device

    cli_vlan_resp = await dut.eapi.cli("show vlan")

    # vlan data is a dictionary, key is the VLAN ID in a string form.
    dev_vlans_info = cli_vlan_resp["vlans"]

    for each_test in testcases.tests:

        # The test-case ID is the VLAN ID in string form.
        vlan_id = each_test.test_case_id()

        for result in eos_test_one_vlan(
            device=device,
            test_case=each_test,
            vlan_id=vlan_id,
            vlan_status=dev_vlans_info.get(vlan_id),
        ):
            yield result


def eos_test_one_vlan(
    device: Device, test_case: VlanTestCase, vlan_id: str, vlan_status: dict
) -> Generator:

    if not vlan_status:
        yield trt.FailNoExistsResult(
            device=device,
            test_case=test_case,
        )
        return

    fails = 0

    # -------------------------------------------------------------------------
    # check that the VLAN is active.
    # -------------------------------------------------------------------------

    msrd_vlan_status = vlan_status["status"]
    if msrd_vlan_status != "active":
        yield trt.FailFieldMismatchResult(
            device=device,
            test_case=test_case,
            field="status",
            measurement=msrd_vlan_status,
        )

    # -------------------------------------------------------------------------
    # check the configured VLAN name value
    # -------------------------------------------------------------------------

    msrd_vlan_name = vlan_status["name"]
    expd_vlan_name = test_case.expected_results.vlan.name

    if msrd_vlan_name != expd_vlan_name:
        yield trt.FailFieldMismatchResult(
            device=device,
            test_case=test_case,
            field="name",
            expected=expd_vlan_name,
            measurement=msrd_vlan_name,
        )
        fails += 1

    # -------------------------------------------------------------------------
    # check the VLAN interface membership list.
    # -------------------------------------------------------------------------

    expd_interfaces = set(test_case.expected_results.interfaces)

    msrd_interfaces = set(
        if_name if if_name != "Cpu" else f"Vlan{vlan_id}"
        for if_name in vlan_status["interfaces"]
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

    # these must be a list in order to JSON serialize.
    msrd_interfaces = list(msrd_interfaces)

    yield trt.PassTestCase(
        device=device,
        test_case=test_case,
        measurement=dict(
            name=msrd_vlan_name,
            status=msrd_vlan_status,
            interfaces=msrd_interfaces,
        ),
    )
