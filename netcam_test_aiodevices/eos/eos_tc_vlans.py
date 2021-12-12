# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device, DeviceInterface
from netcad.netcam import tc_result_types as trt
from netcad.vlan.tc_vlans import VlanTestCases, VlanTestCase

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from netcam_test_aiodevices.eos import EOSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_test_vlans", "eos_test_one_vlan"]


async def eos_test_vlans(self, testcases: VlanTestCases) -> trt.CollectionTestResults:

    dut: EOSDeviceUnderTest = self
    device = dut.device
    results = list()

    # need the configured state, not the optional state since interfaces that
    # are "down" will not show up in the operational state. But the configured
    # state does not include the Cpu/SVI, so need that too.

    cli_vlan_cfg_resp = await dut.eapi.cli("show vlan configured-ports")
    cli_vlan_resp = await dut.eapi.cli("show vlan")

    # vlan data is a dictionary, key is the VLAN ID in a string form. need to
    # merge the contents of the cfg response.  The 'interfaces' key is a
    # dictionary, so we will do an update; so no need to worry about duplicate
    # key handling.

    dev_vlans_info = cli_vlan_resp["vlans"]
    dev_vlans_cfg_info = cli_vlan_cfg_resp["vlans"]
    for vlan_id, vlan_data in dev_vlans_cfg_info.items():
        cfg_interfaces = dev_vlans_cfg_info[vlan_id]["interfaces"]
        dev_vlans_info[vlan_id]["interfaces"].update(cfg_interfaces)

    for test_case in testcases.tests:

        # The test-case ID is the VLAN ID in string form.
        vlan_id = test_case.test_case_id()

        if not (vlan_status := dev_vlans_info.get(vlan_id)):
            results.append(
                trt.FailNoExistsResult(
                    device=device,
                    test_case=test_case,
                )
            )
            continue

        results.extend(
            eos_test_one_vlan(
                device=device,
                test_case=test_case,
                vlan_id=vlan_id,
                vlan_status=vlan_status,
            )
        )

    return results


# -----------------------------------------------------------------------------
#
#                            PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def eos_test_one_vlan(
    device: Device, test_case: VlanTestCase, vlan_id: str, vlan_status: dict
) -> trt.CollectionTestResults:

    results = list()

    # -------------------------------------------------------------------------
    # check that the VLAN is active.
    # -------------------------------------------------------------------------

    msrd_vlan_status = vlan_status["status"]
    if msrd_vlan_status != "active":
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="status",
                measurement=msrd_vlan_status,
            )
        )

    # -------------------------------------------------------------------------
    # check the configured VLAN name value
    # -------------------------------------------------------------------------

    msrd_vlan_name = vlan_status["name"]
    expd_vlan_name = test_case.expected_results.vlan.name

    if msrd_vlan_name != expd_vlan_name:
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="name",
                expected=expd_vlan_name,
                measurement=msrd_vlan_name,
            )
        )

    # -------------------------------------------------------------------------
    # check the VLAN interface membership list.
    # -------------------------------------------------------------------------

    expd_interfaces = set(test_case.expected_results.interfaces)
    expd_sorted = DeviceInterface.sorted_interface_names(expd_interfaces)

    # Map the EOS reported interfaces list into a set for comparitive
    # processing. Do not include any "peer" interfaces; these represent MLAG
    # information. If the VLAN includes a reference to "Cpu", the map that to
    # the "interface Vlan<X>" name.

    msrd_interfaces = set(
        if_name if if_name != "Cpu" else f"Vlan{vlan_id}"
        for if_name in vlan_status["interfaces"]
        if not if_name.startswith("Peer")
    )

    if missing_interfaces := expd_interfaces - msrd_interfaces:
        results.append(
            trt.FailMissingMembersResult(
                device=device,
                test_case=test_case,
                field="interfaces",
                expected=expd_sorted,
                missing=DeviceInterface.sorted_interface_names(missing_interfaces),
            )
        )

    if extra_interfaces := msrd_interfaces - expd_interfaces:
        results.append(
            trt.FailExtraMembersResult(
                device=device,
                test_case=test_case,
                field="interfaces",
                expected=expd_sorted,
                extras=DeviceInterface.sorted_interface_names(extra_interfaces),
            )
        )

    if not any(isinstance(res, trt.FailTestCase) for res in results):
        results.append(
            trt.PassTestCase(
                device=device,
                test_case=test_case,
                measurement=dict(
                    name=msrd_vlan_name,
                    status=msrd_vlan_status,
                    interfaces=DeviceInterface.sorted_interface_names(msrd_interfaces),
                ),
            )
        )

    return results
