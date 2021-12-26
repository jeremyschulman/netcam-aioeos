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
    from netcam_aioeos.eos_dut import EOSDeviceUnderTest

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_check_switchports"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def eos_check_switchports(
    self, switchport_checks: SwitchportCheckCollection
) -> tr.CheckResultsCollection:
    """
    This check executor validates the device operational status of the interface
    switchports.

    Parameters
    ----------
    self:
        The DUT instance for the specific device being checked.

    switchport_checks: SwitchportCheckCollection
        The collection of checks created by the netcad tool for the
        vlans.switchports case.

    Returns
    -------
    A collection of check-results that will be logged and reported to the User
    during check execution and showing results.
    """

    dut: EOSDeviceUnderTest = self
    device = dut.device
    results = list()

    cli_data = await dut.get_switchports()
    map_msrd_swichports = cli_data["switchports"]

    # each check represents one interface to validate.  Loop through each of the
    # checks to ensure that the expected switchport use is as expected.

    for check in switchport_checks.checks:
        expd_status = check.expected_results

        if_name = check.check_id()

        # if the interface from the design does not exist on the device, then
        # report this error and go to next check.

        if not (msrd_port := map_msrd_swichports.get(if_name)):
            results.append(tr.CheckFailNoExists(device=device, check=check))
            continue

        msrd_swpinfo = msrd_port["switchportInfo"]

        # verify the expected switchport mode (access / trunk)

        msrd_mode = msrd_swpinfo["mode"]
        expd_mode = expd_status.switchport_mode

        if expd_mode != msrd_mode:
            results.append(
                tr.CheckFailFieldMismatch(
                    device=device,
                    check=check,
                    field="switchport_mode",
                    measurement=msrd_mode,
                )
            )
            continue

        # validate the interface switchport status depending on if it is access
        # or trunk.

        mode_handler = {
            "access": _check_access_switchport,
            "trunk": _check_trunk_switchport,
        }.get(expd_mode)

        mode_results = mode_handler(dut, check, expd_status, msrd_swpinfo)

        if not any_failures(mode_results):
            mode_results.append(
                tr.CheckPassResult(device=device, check=check, measurement=msrd_swpinfo)
            )

        results.extend(mode_results)

    # return the collection of results for all switchport interfaces
    return results


def _check_access_switchport(
    dut, check, expd_status: SwitchportAccessExpectation, msrd_status: dict
) -> tr.CheckResultsCollection:
    """
    This function validates that the access port is reporting as expected.  This
    primary check here is ensuring the access VLAN-ID matches.
    """

    results = list()

    # EOS stores the vlan id as int, so type comparison AOK

    e_vl_id = expd_status.vlan.vlan_id
    m_vl_id = msrd_status["accessVlanId"]

    if e_vl_id != m_vl_id:
        results.append(
            tr.CheckFailFieldMismatch(
                device=dut.device,
                check=check,
                field="vlan",
                expected=e_vl_id,
                measurement=m_vl_id,
            )
        )

    return results


def _check_trunk_switchport(
    dut, check, expd_status: SwitchportTrunkExpectation, msrd_status: dict
) -> tr.CheckResultsCollection:
    """
    This function validates a trunk switchport against the expected values.
    These checks include matching on the native-vlan and trunk-allowed-vlans.
    """

    results = list()
    device = dut.device

    e_nvl_id = expd_status.native_vlan.vlan_id if expd_status.native_vlan else None
    m_nvl_id = msrd_status["trunkingNativeVlanId"]

    if e_nvl_id and (e_nvl_id != m_nvl_id):
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=check,
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
                check=check,
                field="trunk_allowed_vlans",
                expected=e_tr_alwd_vstr,
                measurement=m_tr_alwd_vstr,
            )
        )

    return results
