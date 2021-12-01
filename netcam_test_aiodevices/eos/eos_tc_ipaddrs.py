# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING
from typing import Generator, AsyncGenerator, Sequence
from itertools import chain


# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.testing_services.ipaddrs import (
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


async def eos_test_ipaddrs(self, testcases: IPInterfacesTestCases) -> AsyncGenerator:

    dut: EOSDeviceUnderTest = self
    device = dut.device
    cli_rsp = await dut.eapi.cli("show ip interface brief")
    dev_ips_data = cli_rsp["interfaces"]

    tc_generators = list()

    if_names = list()

    for test_case in testcases.tests:
        if_name = test_case.test_case_id()
        if_names.append(if_name)

        if not (if_ip_data := dev_ips_data.get(if_name)):
            yield trt.FailNoExistsResult(device=device, test_case=test_case)
            continue

        tc_generators.append(
            eos_test_one_interface(
                device=device, test_case=test_case, msrd_data=if_ip_data
            )
        )

    # only include device interface that have an assigned IP address; this
    # conditional is checked by examining the interface IP address mask length
    # against zero.

    tc_generators.append(
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

    for result in chain.from_iterable(tc_generators):
        yield result


def eos_test_one_interface(
    device: Device, test_case: IPInterfaceTestCase, msrd_data: dict
) -> Generator:

    fails = 0

    # -------------------------------------------------------------------------
    # if there is any error accessing the expect interface IP address
    # information, then yeild a failure and return.
    # -------------------------------------------------------------------------

    try:
        msrd_if_addr = msrd_data["interfaceAddress"]["ipAddr"]
        msrd_if_ipaddr = f"{msrd_if_addr['address']}/{msrd_if_addr['maskLen']}"
    except KeyError:
        yield trt.FailFieldMismatchResult(
            device=device,
            test_case=test_case,
            field="measurement",
            measurement=msrd_data,
        )
        return

    # -------------------------------------------------------------------------
    # Ensure the IP interface value matches.
    # -------------------------------------------------------------------------

    expd_if_ipaddr = test_case.expected_results.if_ipaddr
    if msrd_if_ipaddr != expd_if_ipaddr:
        yield trt.FailFieldMismatchResult(
            device=device,
            test_case=test_case,
            field="if_ipaddr",
            measurement=msrd_if_ipaddr,
        )
        fails += 1

    # -------------------------------------------------------------------------
    # Ensure the IP interface is "up".
    # TODO: should check if the interface is enabled before presuming this
    #       up condition check.
    # -------------------------------------------------------------------------

    if (if_oper := msrd_data["lineProtocolStatus"]) != "up":
        yield trt.FailFieldMismatchResult(
            device=device,
            test_case=test_case,
            field="if_oper",
            expected="up",
            measurement=if_oper,
            error=f"interface for IP {expd_if_ipaddr} is not up: {if_oper}",
        )
        fails += 1

    if fails:
        return

    # -------------------------------------------------------------------------
    # Test Case passes
    # -------------------------------------------------------------------------

    yield trt.PassTestCase(device=device, test_case=test_case, measurement=msrd_data)


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
        result = trt.PassTestCase(device=device, test_case=tc)

    yield result
