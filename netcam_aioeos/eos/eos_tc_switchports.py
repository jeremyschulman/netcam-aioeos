# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.netcam import any_failures
from netcad.checks import check_result_types as tr
from netcad.helpers import range_string

from netcad.vlan.check_switchports import (
    SwitchportCheckCollection,
    SwitchportAccessExpectation,
    SwitchportTrunkExpectation,
)

if TYPE_CHECKING:
    from .eos_dut import EOSDeviceUnderTest

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_tc_switchports"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def eos_tc_switchports(
    self, testcases: SwitchportCheckCollection
) -> tr.CheckResultsCollection:

    dut: EOSDeviceUnderTest = self
    device = dut.device
    results = list()

    cli_data = await dut.get_switchports()
    map_msrd_swichports = cli_data["switchports"]

    for test_case in testcases.checks:
        expd_status = test_case.expected_results

        if_name = test_case.check_id()

        # if the interface from the design does not exist on the device, then
        # report this error and go to next test-case.

        if not (msrd_port := map_msrd_swichports.get(if_name)):
            results.append(tr.CheckFailNoExists(device=device, check=test_case))
            continue

        msrd_swpinfo = msrd_port["switchportInfo"]

        msrd_mode = msrd_swpinfo["mode"]
        expd_mode = expd_status.switchport_mode

        if expd_mode != msrd_mode:
            results.append(
                tr.CheckFailFieldMismatch(
                    device=device,
                    check=test_case,
                    field="switchport_mode",
                    measurement=msrd_mode,
                )
            )
            continue

        mode_handler = {
            "access": _check_access_switchport,
            "trunk": _check_trunk_switchport,
        }.get(expd_mode)

        mode_results = mode_handler(dut, test_case, expd_status, msrd_swpinfo)

        if not any_failures(mode_results):
            mode_results.append(
                tr.CheckPassResult(
                    device=device, check=test_case, measurement=msrd_swpinfo
                )
            )

        results.extend(mode_results)

    return results


def _check_access_switchport(
    dut, test_case, expd_status: SwitchportAccessExpectation, msrd_status: dict
) -> tr.CheckResultsCollection:

    results = list()

    # EOS stores the vlan id as int, so type comparison AOK

    e_vl_id = expd_status.vlan.vlan_id
    m_vl_id = msrd_status["accessVlanId"]

    if e_vl_id != m_vl_id:
        results.append(
            tr.CheckFailFieldMismatch(
                device=dut.device,
                check=test_case,
                field="vlan",
                expected=e_vl_id,
                measurement=m_vl_id,
            )
        )

    return results


def _check_trunk_switchport(
    dut, test_case, expd_status: SwitchportTrunkExpectation, msrd_status: dict
) -> tr.CheckResultsCollection:

    results = list()
    device = dut.device

    e_nvl_id = expd_status.native_vlan.vlan_id if expd_status.native_vlan else None
    m_nvl_id = msrd_status["trunkingNativeVlanId"]

    if e_nvl_id and (e_nvl_id != m_nvl_id):
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=test_case,
                field="native_vlan",
                expected=e_nvl_id,
                measurement=m_nvl_id,
            )
        )

    # EOS stores this as a CSV string, with ranges, for example:
    # 14,16,25-26,29

    e_tr_allowed_vids = sorted(
        [vlan.vlan_id for vlan in expd_status.trunk_allowed_vlans]
    )

    # conver the list of vlan-ids to a range string for string comparison
    # purposes.

    e_tr_alwd_vstr = range_string(e_tr_allowed_vids)
    m_tr_alwd_vstr = msrd_status["trunkAllowedVlans"]

    # if there no expected allowed vlans on this trunk, then set the expected
    # value to "NONE" since that is what EOS reports in this case.

    if not e_tr_alwd_vstr:
        e_tr_alwd_vstr = "NONE"

    if e_tr_alwd_vstr != m_tr_alwd_vstr:
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=test_case,
                field="trunk_allowed_vlans",
                expected=e_tr_alwd_vstr,
                measurement=m_tr_alwd_vstr,
            )
        )

    return results
