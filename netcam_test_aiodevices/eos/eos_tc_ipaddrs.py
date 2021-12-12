# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING
from typing import Generator, Sequence

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.topology.tc_ipaddrs import (
    IPInterfacesTestCases,
    IPInterfaceTestCase,
    IPInterfaceExclusiveListTestCase,
)

from netcad.device import Device
from netcad.netcam import tc_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from netcam_test_aiodevices.eos import EOSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_test_ipaddrs"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def eos_test_ipaddrs(
    self, testcases: IPInterfacesTestCases
) -> trt.CollectionTestResults:

    dut: EOSDeviceUnderTest = self
    device = dut.device
    cli_rsp = await dut.eapi.cli("show ip interface brief")
    dev_ips_data = cli_rsp["interfaces"]

    results = list()
    if_names = list()

    for test_case in testcases.tests:
        if_name = test_case.test_case_id()
        if_names.append(if_name)

        if not (if_ip_data := dev_ips_data.get(if_name)):
            results.append(
                trt.FailNoExistsResult(
                    device=device, test_case=test_case, field="if_ipaddr"
                )
            )
            continue

        one_results = await eos_test_one_interface(
            dut, device=device, test_case=test_case, msrd_data=if_ip_data
        )

        results.extend(one_results)

    # only include device interface that have an assigned IP address; this
    # conditional is checked by examining the interface IP address mask length
    # against zero.

    results.extend(
        eos_test_exclusive_list(
            device=device,
            expd_if_names=if_names,
            msrd_if_names=[
                if_ip_data["name"]
                for if_ip_data in dev_ips_data.values()
                if if_ip_data["interfaceAddress"]["ipAddr"]["maskLen"] != 0
            ],
        )
    )

    return results


# -----------------------------------------------------------------------------


async def eos_test_one_interface(
    dut: "EOSDeviceUnderTest",
    device: Device,
    test_case: IPInterfaceTestCase,
    msrd_data: dict,
) -> trt.CollectionTestResults:

    results = list()

    # get the interface name begin tested

    if_name = test_case.test_case_id()

    # -------------------------------------------------------------------------
    # if there is any error accessing the expect interface IP address
    # information, then yeild a failure and return.
    # -------------------------------------------------------------------------

    try:
        msrd_if_addr = msrd_data["interfaceAddress"]["ipAddr"]
        msrd_if_ipaddr = f"{msrd_if_addr['address']}/{msrd_if_addr['maskLen']}"

    except KeyError:
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="measurement",
                measurement=msrd_data,
            )
        )
        return results

    # -------------------------------------------------------------------------
    # Ensure the IP interface value matches.
    # -------------------------------------------------------------------------

    expd_if_ipaddr = test_case.expected_results.if_ipaddr
    if msrd_if_ipaddr != expd_if_ipaddr:
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="if_ipaddr",
                measurement=msrd_if_ipaddr,
            )
        )

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

    if iface_enabled and (if_oper := msrd_data["lineProtocolStatus"]) != "up":

        # if the interface is an SVI, then we need to check to see if _all_ of
        # the associated physical interfaces are either disabled or in a
        # reseverd condition.

        if if_name.startswith("Vlan"):
            await _check_vlan_assoc_interface(
                dut, test_case, if_name=if_name, msrd_ipifaddr_oper=if_oper
            )
        else:
            results.append(
                trt.FailFieldMismatchResult(
                    device=device,
                    test_case=test_case,
                    field="if_oper",
                    expected="up",
                    measurement=if_oper,
                    error=f"interface for IP {expd_if_ipaddr} is not up: {if_oper}",
                )
            )

    if not any(isinstance(res, trt.FailTestCase) for res in results):
        results.append(
            trt.PassTestCase(device=device, test_case=test_case, measurement=msrd_data)
        )

    return results


def eos_test_exclusive_list(
    device: Device, expd_if_names: Sequence[str], msrd_if_names: Sequence[str]
) -> Generator:

    # the previous per-interface checks for any missing; therefore we only need
    # to check for any extra interfaces found on the device.

    tc = IPInterfaceExclusiveListTestCase()

    if extras := set(msrd_if_names) - set(expd_if_names):
        result = trt.FailExtraMembersResult(
            device=device,
            test_case=tc,
            field="ip-interfaces",
            expected=sorted(expd_if_names),
            extras=sorted(extras),
        )
    else:
        result = trt.PassTestCase(device=device, test_case=tc, measurement="exists")

    yield result


async def _check_vlan_assoc_interface(
    dut: "EOSDeviceUnderTest", test_case, if_name: str, msrd_ipifaddr_oper
) -> trt.CollectionTestResults:
    """
    This coroutine is used to check whether or not a VLAN SVI ip address is not
    "up" due to the fact that the underlying interfaces are either disabled or
    in a "reserved" design; meaning we do not care if they are up or down. If
    the SVI is down because of this condition, the test case will "pass", and an
    information record is yielded to inform the User.

    Parameters
    ----------
    dut:
        The device under test

    test_case:
        The specific test case

    if_name:
        The specific VLAN SVI name, "Vlan12" for example:

    msrd_ipifaddr_oper:
        The measured opertional state of the IP interface

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

    results = list()

    for check_ifname in vlan_cfgd_ifnames:
        dut_iface = dut_ifs[check_ifname]
        if (dut_iface["enabled"] is False) or (
            "is_reserved" in dut_iface["profile_flags"]
        ):
            disrd_ifnames.add(check_ifname)

    if disrd_ifnames == vlan_cfgd_ifnames:
        results.append(
            trt.InfoTestCase(
                device=dut.device,
                test_case=test_case,
                field="if_oper",
                measurement=dict(
                    if_oper=msrd_ipifaddr_oper,
                    interfaces=list(vlan_cfgd_ifnames),
                    message="interfaces are either disabled or in reserved state",
                ),
            )
        )

        results.append(
            trt.PassTestCase(
                device=dut.device, test_case=test_case, measurement="exists"
            )
        )
        return results

    results.append(
        trt.FailFieldMismatchResult(
            device=dut.device,
            test_case=test_case,
            field="if_oper",
            expected="up",
            measurement=msrd_ipifaddr_oper,
            error=f"interface for IP {test_case.expected_results.if_ipaddr} is not up: {msrd_ipifaddr_oper}",
        )
    )
