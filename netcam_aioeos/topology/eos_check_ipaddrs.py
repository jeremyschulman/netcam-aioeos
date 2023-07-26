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

from typing import Sequence

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.topology.checks.check_ipaddrs import (
    IPInterfacesCheckCollection,
    IPInterfaceCheck,
    IPInterfaceCheckResult,
    IPInterfaceExclusiveListCheck,
    IPInterfaceExclusiveListCheckResult,
)

from netcad.device import Device, DeviceInterface
from netcad.checks import CheckResultsCollection, CheckStatus

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = []


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


@EOSDeviceUnderTest.execute_checks.register  # noqa
async def eos_test_ipaddrs(
    dut, collection: IPInterfacesCheckCollection
) -> CheckResultsCollection:
    """
    This check executor validates the IP addresses used on the device against
    those that are defined in the design.
    """

    dut: EOSDeviceUnderTest

    device = dut.device
    cli_rsp = await dut.eapi.cli("show ip interface brief")
    dev_ips_data = cli_rsp["interfaces"]

    results = list()
    if_names = list()

    for check in collection.checks:
        if_name = check.check_id()
        if_names.append(if_name)

        # if the IP address does not exist, then report that measurement and
        # move on to the next interface.

        if not (if_ip_data := dev_ips_data.get(if_name)):
            results.append(
                IPInterfaceCheckResult(
                    device=device, check=check, measurement=None
                ).measure()
            )
            continue

        await eos_test_one_interface(
            dut, device=device, check=check, msrd_data=if_ip_data, results=results
        )

    # only include device interface that have an assigned IP address; this
    # conditional is checked by examining the interface IP address mask length
    # against zero.

    if collection.exclusive:
        eos_test_exclusive_list(
            device=device,
            expd_if_names=if_names,
            msrd_if_names=[
                if_ip_data["name"]
                for if_ip_data in dev_ips_data.values()
                if if_ip_data["interfaceAddress"]["ipAddr"]["maskLen"] != 0
            ],
            results=results,
        )

    return results


# -----------------------------------------------------------------------------


async def eos_test_one_interface(
    dut: "EOSDeviceUnderTest",
    device: Device,
    check: IPInterfaceCheck,
    msrd_data: dict,
    results: CheckResultsCollection,
):
    """
    This function validates a specific interface use of an IP address against
    the design expectations.
    """

    if_name = check.check_id()
    result = IPInterfaceCheckResult(device=device, check=check)
    msrd = result.measurement

    # -------------------------------------------------------------------------
    # if there is any error accessing extracting interface IP address
    # information, then yeild a failure and return.
    # -------------------------------------------------------------------------

    try:
        msrd_if_addr = msrd_data["interfaceAddress"]["ipAddr"]
        msrd.if_ipaddr = f"{msrd_if_addr['address']}/{msrd_if_addr['maskLen']}"

    except KeyError:
        result.measurement = None
        results.append(result.measure())
        return results

    # -------------------------------------------------------------------------
    # Ensure the IP interface value matches.
    # -------------------------------------------------------------------------

    expd_if_ipaddr = check.expected_results.if_ipaddr

    # if the IP address is marked as "is_reserved" it means that an external
    # entity configured the IP address, and this check will only record the
    # value as an INFO check result.

    if expd_if_ipaddr == "is_reserved":
        result.status = CheckStatus.INFO
        results.append(result.measure())

    # -------------------------------------------------------------------------
    # Ensure the IP interface is "up".
    # TODO: should check if the interface is enabled before presuming this
    #       up condition check.
    # -------------------------------------------------------------------------

    # check to see if the interface is disabled before we check to see if the IP
    # address is in the up condition.

    dut_interfaces = dut.device_info["interfaces"]
    dut_iface = dut_interfaces[if_name]
    iface_enabled = dut_iface["enabled"] is True

    msrd.oper_up = msrd_data["lineProtocolStatus"] == "up"

    if iface_enabled and not msrd.oper_up:
        # if the interface is an SVI, then we need to check to see if _all_ of
        # the associated physical interfaces are either disabled or in a
        # reseverd condition.

        if if_name.startswith("Vlan"):
            await _check_vlan_assoc_interface(
                dut, if_name=if_name, result=result, results=results
            )
            return results

    results.append(result.measure())
    return results


def eos_test_exclusive_list(
    device: Device,
    expd_if_names: Sequence[str],
    msrd_if_names: Sequence[str],
    results: CheckResultsCollection,
):
    """
    This check determines if there are any extra IP Interfaces defined on the
    device that are not expected per the design.
    """

    # the previous per-interface checks for any missing; therefore we only need
    # to check for any extra interfaces found on the device.

    def sort_key(i):
        return DeviceInterface(i, interfaces=device.interfaces)

    result = IPInterfaceExclusiveListCheckResult(
        device=device,
        check=IPInterfaceExclusiveListCheck(expected_results=expd_if_names),
        measurement=sorted(msrd_if_names, key=sort_key),
    )
    results.append(result.measure())


async def _check_vlan_assoc_interface(
    dut: EOSDeviceUnderTest,
    if_name: str,
    result: IPInterfaceCheckResult,
    results: CheckResultsCollection,
):
    """
    This function is used to check whether a VLAN SVI ip address is not "up"
    due to the fact that the underlying interfaces are either disabled or in a
    "reserved" design; meaning we do not care if they are up or down. If the
    SVI is down because of this condition, the test case will "pass", and an
    information record is yielded to inform the User.

    Parameters
    ----------
    dut:
        The device under test

    result:
        The result instance bound to the check

    if_name:
        The specific VLAN SVI name, "Vlan12" for example:

    Yields
    ------
    netcad test case results; one or more depending on the condition of SVI
    interfaces.
    """

    vlan_id = if_name.split("Vlan")[-1]
    cli_res = await dut.eapi.cli(f"show vlan id {vlan_id} configured-ports")
    vlan_cfgd_ifnames = set(cli_res["vlans"][vlan_id]["interfaces"])
    disrd_ifnames = set()
    dut_ifs = dut.device_info["interfaces"]

    for check_ifname in vlan_cfgd_ifnames:
        dut_iface = dut_ifs[check_ifname]
        if (dut_iface["enabled"] is False) or (
            "is_reserved" in dut_iface["profile_flags"]
        ):
            disrd_ifnames.add(check_ifname)

    if disrd_ifnames == vlan_cfgd_ifnames:
        # then the SVI check should be a PASS because of the conditions
        # mentioned.

        result.logs.INFO(
            "oper_up",
            dict(
                message="interfaces are either disabled or in reserved state",
                interfaces=list(vlan_cfgd_ifnames),
            ),
        )

        def on_mismatch(_field, _expd, _msrd):
            return CheckStatus.PASS if _field == "oper_up" else CheckStatus.FAIL

        results.append(result.measure(on_mismatch=on_mismatch))

    # results.append(
    #     trt.CheckFailFieldMismatch(
    #         device=dut.device,
    #         check=check,
    #         field="if_oper",
    #         expected="up",
    #         measurement=msrd_ipifaddr_oper,
    #         error=f"interface for IP {check.expected_results.if_ipaddr} is not up: {msrd_ipifaddr_oper}",
    #     )
    # )

    return results
