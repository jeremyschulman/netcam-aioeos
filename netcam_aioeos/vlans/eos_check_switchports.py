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
# Public Imports
# -----------------------------------------------------------------------------

from netcad.checks import CheckResultsCollection, CheckStatus

from netcad.helpers import range_string

from netcad.vlans.checks.check_switchports import (
    SwitchportCheckCollection,
    SwitchportCheck,
    SwitchportCheckResult,
)

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


@EOSDeviceUnderTest.execute_checks.register
async def eos_check_switchports(
    self, switchport_checks: SwitchportCheckCollection
) -> CheckResultsCollection:
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
        result = SwitchportCheckResult(device=device, check=check)

        expd_status = check.expected_results

        if_name = check.check_id()

        # if the interface from the design does not exist on the device, then
        # report this error and go to next check.

        if not (msrd_port := map_msrd_swichports.get(if_name)):
            result.measurement = None
            results.append(result.measure())
            continue

        msrd_swpinfo = msrd_port["switchportInfo"]

        # verify the expected switchport mode (access / trunk)
        match expd_status.switchport_mode:
            case "access":
                _check_access_switchport(
                    result=result, msrd_status=msrd_swpinfo, results=results
                )
            case "trunk":
                _check_trunk_switchport(
                    result=result, msrd_status=msrd_swpinfo, results=results
                )

    # return the collection of results for all switchport interfaces
    return results


def _check_access_switchport(
    result: SwitchportCheckResult, msrd_status: dict, results: CheckResultsCollection
):
    """
    This function validates that the access port is reporting as expected.
    This primary check here is ensuring the access VLAN-ID matches.
    """

    msrd: SwitchportCheckResult.MeasuredAccess = result.measurement

    msrd.switchport_mode = msrd_status["mode"]

    # EOS stores the vlan id as int, so type comparison AOK
    msrd.vlan = msrd_status["accessVlanId"]
    results.append(result.measure())


def _check_trunk_switchport(
    result: SwitchportCheckResult, msrd_status: dict, results: CheckResultsCollection
):
    """
    This function validates a trunk switchport against the expected values.
    These checks include matching on the native-vlan and trunk-allowed-vlans.
    """

    expd: SwitchportCheck.ExpectTrunk = result.check.expected_results
    msrd: SwitchportCheckResult.MeasuredTrunk = result.measurement

    msrd.switchport_mode = msrd_status["mode"]
    msrd.native_vlan = msrd_status["trunkingNativeVlanId"]

    # EOS stores this as a CSV string, with ranges, for example:
    # 14,16,25-26,29

    e_tr_allowed_vids = sorted([vlan.vlan_id for vlan in expd.trunk_allowed_vlans])

    # conver the list of vlan-ids to a range string for string comparison
    # purposes.

    e_tr_alwd_vstr = range_string(e_tr_allowed_vids)
    m_tr_alwd_vstr = msrd_status["trunkAllowedVlans"]

    # if there is no expected allowed vlans on this trunk, then set the expected
    # value to "NONE" since that is what EOS reports in this case.

    if not e_tr_alwd_vstr:
        e_tr_alwd_vstr = "NONE"

    def on_mismatch(_field, _expd, _msrd):
        if _field == "trunk_allowed_vlans":
            if e_tr_alwd_vstr == m_tr_alwd_vstr:
                return CheckStatus.PASS

    results.append(result.measure(on_mismatch=on_mismatch))
