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

from typing import TYPE_CHECKING, Set
from operator import attrgetter

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device, DeviceInterface
from netcad.netcam import any_failures
from netcad.checks import check_result_types as trt
from netcad.vlan.check_vlans import VlanCheckCollection, VlanCheck

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from netcam_aioeos.eos_dut import EOSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_check_vlans", "eos_check_one_vlan"]


async def eos_check_vlans(
    self, vlan_checks: VlanCheckCollection
) -> trt.CheckResultsCollection:

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

    msrd_active_vlan_ids = {
        int(vlan_id)
        for vlan_id, vlan_st in dev_vlans_info.items()
        if vlan_st["status"] == "active"
    }

    for vlan_id, vlan_data in dev_vlans_cfg_info.items():
        cfg_interfaces = dev_vlans_cfg_info[vlan_id]["interfaces"]
        dev_vlans_info[vlan_id]["interfaces"].update(cfg_interfaces)

    for check in vlan_checks.checks:

        # The check ID is the VLAN ID in string form.
        vlan_id = check.check_id()

        if not (vlan_status := dev_vlans_info.get(vlan_id)):
            results.append(
                trt.CheckFailNoExists(
                    device=device,
                    check=check,
                )
            )
            continue

        results.extend(
            eos_check_one_vlan(
                device=device, check=check, vlan_id=vlan_id, vlan_status=vlan_status
            )
        )

    results.extend(
        eos_check_vlan_exl_list(
            device=device,
            check=vlan_checks.exclusive,
            expd_vlan_ids=set(
                map(attrgetter("vlan_id"), vlan_checks.exclusive.expected_results.vlans)
            ),
            msrd_vlan_ids=msrd_active_vlan_ids,
        )
    )

    return results


# -----------------------------------------------------------------------------
#
#                            PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def eos_check_vlan_exl_list(
    device: Device,
    check,
    expd_vlan_ids: Set,
    msrd_vlan_ids: Set,
) -> trt.CheckResultsCollection:
    """
    This function checks to see if there are any VLANs measured on the device
    that are not in the expected exclusive list.  We do not need to check for
    missing VLANs since expected per-vlan checks have already been performed.
    """

    if extras := msrd_vlan_ids - expd_vlan_ids:
        return [
            trt.CheckFailExtraMembers(
                device=device,
                check=check,
                field=check.check_id(),
                expected=sorted(expd_vlan_ids),
                extras=sorted(extras),
            )
        ]

    return [
        trt.CheckPassResult(
            device=device, check=check, measurement=sorted(msrd_vlan_ids)
        )
    ]


def eos_check_one_vlan(
    device: Device, check: VlanCheck, vlan_id: str, vlan_status: dict
) -> trt.CheckResultsCollection:

    results = list()

    # -------------------------------------------------------------------------
    # check that the VLAN is active.
    # -------------------------------------------------------------------------

    msrd_vlan_status = vlan_status["status"]
    if msrd_vlan_status != "active":
        results.append(
            trt.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="status",
                measurement=msrd_vlan_status,
            )
        )

    # -------------------------------------------------------------------------
    # check the configured VLAN name value
    # -------------------------------------------------------------------------

    msrd_vlan_name = vlan_status["name"]
    expd_vlan_name = check.expected_results.vlan.name

    if msrd_vlan_name != expd_vlan_name:
        results.append(
            trt.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="name",
                expected=expd_vlan_name,
                measurement=msrd_vlan_name,
            )
        )

    # -------------------------------------------------------------------------
    # check the VLAN interface membership list.
    # -------------------------------------------------------------------------

    expd_interfaces = set(check.expected_results.interfaces)
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
            trt.CheckFailMissingMembers(
                device=device,
                check=check,
                field="interfaces",
                expected=expd_sorted,
                missing=DeviceInterface.sorted_interface_names(missing_interfaces),
            )
        )

    if extra_interfaces := msrd_interfaces - expd_interfaces:
        results.append(
            trt.CheckFailExtraMembers(
                device=device,
                check=check,
                field="interfaces",
                expected=expd_sorted,
                extras=DeviceInterface.sorted_interface_names(extra_interfaces),
            )
        )

    if not any_failures(results):
        results.append(
            trt.CheckPassResult(
                device=device,
                check=check,
                measurement=dict(
                    name=msrd_vlan_name,
                    status=msrd_vlan_status,
                    interfaces=DeviceInterface.sorted_interface_names(msrd_interfaces),
                ),
            )
        )

    return results
