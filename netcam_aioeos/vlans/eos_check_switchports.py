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

from typing import cast

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.checks import CheckResultsCollection

from netcad.helpers import range_string, parse_istrange

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
    dut, switchport_checks: SwitchportCheckCollection
) -> CheckResultsCollection:
    """
    This check executor validates the device operational status of the interface
    switchports.

    Parameters
    ----------
    dut:
        The DUT instance for the specific device being checked.

    switchport_checks: SwitchportCheckCollection
        The collection of checks created by the netcad tool for the
        vlans.switchports case.

    Returns
    -------
    A collection of check-results that will be logged and reported to the User
    during check execution and showing results.
    """

    dut: EOSDeviceUnderTest
    device = dut.device
    results = list()

    cli_data = await dut.get_switchports()
    map_msrd_swichports = cli_data["switchports"]

    # each check represents one interface to validate.  Loop through each of the
    # checks to ensure that the expected switchport use is as expected.

    for check in switchport_checks.checks:
        result = SwitchportCheckResult(device=device, check=check)

        expd_status = cast(SwitchportCheck.ExpectSwitchport, check.expected_results)

        if_name = check.check_id()

        # if the interface from the design does not exist on the device, then
        # report this error and go to next check.

        if not (msrd_port := map_msrd_swichports.get(if_name)):
            result.measurement = None
            results.append(result.measure())
            continue

        # ensure the expected port mode matches before calling the specific
        # mode check.  if there is a mismatch, then fail now.

        msrd_swpinfo = msrd_port["switchportInfo"]
        if expd_status.switchport_mode != (msrd_mdoe := msrd_swpinfo["mode"]):
            result.measurement = SwitchportCheckResult.Measurement()
            result.measurement.switchport_mode = msrd_mdoe
            results.append(result.measure())
            continue

        # verify the expected switchport mode (access / trunk)
        (
            _check_access_switchport
            if expd_status.switchport_mode == "access"
            else _check_trunk_switchport
        )(result=result, msrd_status=msrd_swpinfo, results=results)

    # return the collection of results for all switchport interfaces
    return results


def _check_access_switchport(
    result: SwitchportCheckResult, msrd_status: dict, results: CheckResultsCollection
):
    """
    This function validates that the access port is reporting as expected.
    This primary check here is ensuring the access VLAN-ID matches.
    """

    msrd = result.measurement = SwitchportCheckResult.MeasuredAccess()
    msrd.switchport_mode = msrd_status["mode"]

    # the check stores the VlanProfile, and we need to mutate this value to the
    # VLAN ID for comparitor reason.
    result.check.expected_results.vlan = result.check.expected_results.vlan.vlan_id

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

    expd = cast(SwitchportCheck.ExpectTrunk, result.check.expected_results)
    msrd = result.measurement = SwitchportCheckResult.MeasuredTrunk()
    msrd.switchport_mode = msrd_status["mode"]
    msrd.native_vlan = msrd_status["trunkingNativeVlanId"]

    # conver the expected list of vlan-ids to a range string for string
    # comparison purposes. EOS stores this as a CSV string, with ranges, for
    # example: 14,16,25-26,29.  EOS stores the value "ALL" when there are no
    # explicitly allowed values configured on the interface.

    # mutate the expected values that are in the form of VlanProfile into their
    # measureable counterparts.

    if expd.trunk_allowed_vlans:
        expd_allowed_vids = sorted([vlan.vlan_id for vlan in expd.trunk_allowed_vlans])
        expd.trunk_allowed_vlans = range_string(expd_allowed_vids)
    else:
        expd.trunk_allowed_vlans = "ALL"

    if expd.native_vlan:
        expd.native_vlan = expd.native_vlan.vlan_id

    msrd.trunk_allowed_vlans = msrd_status["trunkAllowedVlans"]

    def on_mismatch(_field, _expd_v, _msrd_v):
        if _field != "trunk_allowed_vlans":
            return

        _msrd_v_set = parse_istrange(_msrd_v)

        _expd_v_set = set(expd_allowed_vids)
        _info = dict()
        if _missing := _expd_v_set - _msrd_v_set:
            _info["missing"] = _missing
        if _extra := _msrd_v_set - _expd_v_set:
            _info["extra"] = _extra

        result.logs.INFO("trunk_allowed_vlans_mismatch", _info)

    results.append(result.measure(on_mismatch=on_mismatch))
