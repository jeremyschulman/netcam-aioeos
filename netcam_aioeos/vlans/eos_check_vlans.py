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

from typing import Set

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device
from netcad.checks import CheckResultsCollection, CheckStatus

from netcad.vlans.checks.check_vlans import (
    VlanCheckCollection,
    VlanCheckResult,
    VlanExclusiveListCheck,
    VlanExclusiveListCheckResult,
)

from netcad.vlans import VlanDesignServiceConfig

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_check_vlans", "eos_check_one_vlan"]


@EOSDeviceUnderTest.execute_checks.register  # noqa
async def eos_check_vlans(
    self, vlan_checks: VlanCheckCollection
) -> CheckResultsCollection:
    """
    This check executor validates tha the device has the VLANs expected by the
    design.  These checks include validating the VLANs exist as they should in
    the design (for example VLAN-10 is "Printers" and not "VideoSystesms").
    This exector also validates the exclusive list of VLANs to ensure the device
    is not configured with any unexpected VLANs.
    """

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

    ds_config = VlanDesignServiceConfig.parse_obj(vlan_checks.config)
    if not ds_config.check_vlan1:
        dev_vlans_info.pop("1")
        dev_vlans_cfg_info.pop("1")

    msrd_active_vlan_ids = {
        int(vlan_id)
        for vlan_id, vlan_st in dev_vlans_info.items()
        if vlan_st["status"] == "active"
    }

    for vlan_id, vlan_data in dev_vlans_cfg_info.items():
        cfg_interfaces = dev_vlans_cfg_info[vlan_id]["interfaces"]
        dev_vlans_info[vlan_id]["interfaces"].update(cfg_interfaces)

    # keep track of the set of expectd VLAN-IDs (ints) should we need them for
    # the exclusivity check.

    expd_vlan_ids = set()

    for check in vlan_checks.checks:
        result = VlanCheckResult(device=device, check=check)

        # The check ID is the VLAN ID in string form.

        vlan_id = check.check_id()
        expd_vlan_ids.add(vlan_id)

        # If the VLAN data is missing from the device, then we are done.

        if not (vlan_status := dev_vlans_info.get(vlan_id)):
            result.measurement = None
            results.append(result.measure())
            continue

        eos_check_one_vlan(
            exclusive=vlan_checks.exclusive,
            vlan_status=vlan_status,
            result=result,
            results=results,
        )

    if vlan_checks.exclusive:
        _check_exclusive(
            device=device,
            expd_vlan_ids=expd_vlan_ids,
            msrd_vlan_ids=msrd_active_vlan_ids,
            results=results,
        )

    return results


# -----------------------------------------------------------------------------
#
#                            PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def _check_exclusive(
    device: Device,
    expd_vlan_ids: Set,
    msrd_vlan_ids: Set,
    results: CheckResultsCollection,
):
    """
    This function checks to see if there are any VLANs measured on the device
    that are not in the expected exclusive list.  We do not need to check for
    missing VLANs since expected per-vlan checks have already been performed.
    """

    result = VlanExclusiveListCheckResult(
        device=device,
        check=VlanExclusiveListCheck(expected_results=sorted(expd_vlan_ids)),
        measurement=sorted(msrd_vlan_ids),
    )
    results.append(result.measure())


def eos_check_one_vlan(
    exclusive: bool,
    result: VlanCheckResult,
    vlan_status: dict,
    results: CheckResultsCollection,
):
    """
    Checks a specific VLAN to ensure that it exists on the device as expected.
    """

    check = result.check
    msrd = result.measurement

    vlan_id = check.check_id()

    msrd.oper_up = vlan_status["status"] == "active"
    msrd.name = vlan_status["name"]

    # -------------------------------------------------------------------------
    # check the VLAN interface membership list.
    # -------------------------------------------------------------------------

    # Map the EOS reported interfaces list into a set for comparitive
    # processing. Do not include any "peer" interfaces; these represent MLAG
    # information. If the VLAN includes a reference to "Cpu", the map that to
    # the "interface Vlan<X>" name.

    msrd.interfaces = [
        if_name if if_name != "Cpu" else f"Vlan{vlan_id}"
        for if_name in vlan_status["interfaces"]
        if not if_name.startswith("Peer")
    ]

    msrd_ifs_set = set(msrd.interfaces)
    expd_ifs_set = set(check.expected_results.interfaces)

    if exclusive:
        if missing_interfaces := expd_ifs_set - msrd_ifs_set:
            result.logs.FAIL("interfaces", dict(missing=list(missing_interfaces)))

        if extra_interfaces := msrd_ifs_set - expd_ifs_set:
            result.logs.FAIL("interfaces", dict(extra=list(extra_interfaces)))

    def on_mismatch(_field, _expd, _msrd):
        if _field == "name":
            # if the VLAN name is not set, then we do not check-validate the
            # configured name.  This was added to support design-unused-vlan1;
            # but could be used for any VLAN.

            if not _expd:
                return CheckStatus.PASS

            result.logs.WARN(_field, dict(expected=_expd, measured=_msrd))
            return CheckStatus.PASS

        if _field == "interfaces":
            if exclusive:
                # use the sets for comparison purposes to avoid mismatch
                # due to list order.
                if msrd_ifs_set == expd_ifs_set:
                    return CheckStatus.PASS
            else:
                # if the set of measured interfaces are in the set of expected, and
                # this check is non-exclusive, then pass it.
                if msrd_ifs_set & expd_ifs_set == expd_ifs_set:
                    return CheckStatus.PASS

    results.append(result.measure(on_mismatch=on_mismatch))
