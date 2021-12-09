# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------
import re
from typing import TYPE_CHECKING, Generator, AsyncGenerator, Set
from itertools import chain
from operator import attrgetter

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from pydantic import BaseModel

from netcad.device import Device, DeviceInterface
from netcad.netcam import tc_result_types as tr

from netcad.testing_services.interfaces import (
    InterfaceListTestCase,
    InterfaceTestCases,
    InterfaceTestCase,
)

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from netcam_test_aiodevices.eos import EOSDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_tc_interfaces", "eos_test_one_interface", "eos_test_one_svi"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------

_match_svi = re.compile(r"Vlan(\d+)").match


async def eos_tc_interfaces(self, testcases: InterfaceTestCases) -> AsyncGenerator:
    """
    This async generator is responsible for implementing the "interfaces" test
    cases for EOS devices.

    Notes
    ------
    This function is **IMPORTED** directly into the DUT class so that these
    testcase files can be separated.

    Parameters
    ----------
    self: <!LEAVE UNHINTED!>
        The DUT instance for the EOS device

    testcases: InterfaceTestCases
        The testcases instance that contains the specific testing details.

    Yields
    ------
    TestCasePass, TestCaseFailed
    """

    dut: EOSDeviceUnderTest = self
    device = dut.device

    # read the data from the EOS device for both "show interfaces ..." and "show
    # vlan ..." since we need both.

    cli_sh_ifaces, cli_sh_vlan, cli_sh_ipinf = await dut.eapi.cli(
        commands=[
            "show interfaces status",
            "show vlan brief",
            "show ip interface brief",
        ]
    )

    map_if_oper_data: dict = cli_sh_ifaces["interfaceStatuses"]
    map_svi_oper_data: dict = cli_sh_vlan["vlans"]
    map_ip_ifaces: dict = cli_sh_ipinf["interfaces"]

    # -------------------------------------------------------------------------
    # Check for the exclusive set of interfaces expected vs actual.
    # -------------------------------------------------------------------------

    for result in eos_check_interfaces_list(
        device=device,
        expd_interfaces=set(test_case.test_case_id() for test_case in testcases.tests),
        msrd_interfaces=set(chain(map_if_oper_data, map_ip_ifaces)),
    ):
        yield result

    # -------------------------------------------------------------------------
    # Check each interface for health checks
    # -------------------------------------------------------------------------

    for test_case in testcases.tests:

        if_name = test_case.test_case_id()

        # ---------------------------------------------------------------------
        # if the interface is a SVI, that is begins with "Vlan", then we need to
        # examine it differently since it does not show up in the "show
        # interfaces ..." command.
        # ---------------------------------------------------------------------

        if vlan_mo := _match_svi(if_name):

            # extract the VLAN ID value from the interface name; the lookup is a
            # int-as-string since that is how the data is encoded in the CLI
            # response object.  If the VLAN does not exist, or if the VLAN does
            # exist but there is no Cpu interface, then the "interface Vlan<N>"
            # does not exist on the device.

            vlan_id = vlan_mo.group(1)
            svi_oper_status = map_svi_oper_data.get(vlan_id)

            if not (svi_oper_status or "Cpu" not in svi_oper_status["interfaces"]):
                yield tr.FailNoExistsResult(device=device, test_case=test_case)
                continue

            for result in eos_test_one_svi(
                device=device, test_case=test_case, svi_oper_status=svi_oper_status
            ):
                yield result

            # done with Vlan interface, go to next test-case
            continue

        # ---------------------------------------------------------------------
        # If the interface is a Loopback ...
        # ---------------------------------------------------------------------

        if if_name.startswith("Loopback"):
            if not (lo_status := map_ip_ifaces.get(if_name)):
                yield tr.FailNoExistsResult(device=device, test_case=test_case)
                continue

            for result in eos_test_one_loopback(
                device=device, test_case=test_case, ifip_oper_status=lo_status
            ):
                yield result

            # done with Loopback, go to next test-case
            continue

        # ---------------------------------------------------------------------
        # The interface is not an SVI, look into the "show interfaces ..."
        # output. if the interface does not exist on the device, then the test
        # fails, and we go onto the next text.
        # ---------------------------------------------------------------------

        if not (iface_oper_status := map_if_oper_data.get(if_name)):
            yield tr.FailNoExistsResult(device=device, test_case=test_case)
            continue

        for result in eos_test_one_interface(
            device=device,
            test_case=test_case,
            iface_oper_status=iface_oper_status,
        ):
            yield result


# -----------------------------------------------------------------------------
#
#                       PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def eos_check_interfaces_list(
    device: Device, expd_interfaces: Set[str], msrd_interfaces: Set[str]
) -> Generator:

    fails = 0

    tc = InterfaceListTestCase()
    attr_name = attrgetter("name")
    expd_sorted = list(map(attr_name, sorted(map(DeviceInterface, expd_interfaces))))

    if missing_interfaces := expd_interfaces - msrd_interfaces:
        fails += 1
        msng_sorted = list(
            map(attr_name, sorted(map(DeviceInterface, missing_interfaces)))
        )
        yield tr.FailMissingMembersResult(
            device=device,
            test_case=tc,
            field="interfaces",
            expected=expd_sorted,
            missing=msng_sorted,
        )

    if extra_interfaces := msrd_interfaces - expd_interfaces:
        fails += 1
        exta_sorted = list(
            map(attr_name, sorted(map(DeviceInterface, extra_interfaces)))
        )

        yield tr.FailExtraMembersResult(
            device=device,
            test_case=tc,
            field="interfaces",
            expected=expd_sorted,
            extras=exta_sorted,
        )

    if fails:
        return

    yield tr.PassTestCase(
        device=device, test_case=tc, measurement="OK: no extra or missing interfaces"
    )


# -----------------------------------------------------------------------------
# EOS Measurement dataclass
# -----------------------------------------------------------------------------

BITS_TO_MBS = 10 ** -6


class EosInterfaceMeasurement(BaseModel):
    """
    This dataclass is used to store the values as retrieved from the EOS device
    into a set of attributes that align to the test-case.
    """

    used: bool
    oper_up: bool
    desc: str
    speed: int

    @classmethod
    def from_cli(cls, cli_payload: dict):
        """returns an EOS specific measurement mapping the CLI object fields"""
        return cls(
            used=cli_payload["linkStatus"] != "disabled",
            oper_up=cli_payload["lineProtocolStatus"] == "up",
            desc=cli_payload["description"],
            speed=cli_payload["bandwidth"] * BITS_TO_MBS,
        )


def eos_test_one_interface(
    device: Device, test_case: InterfaceTestCase, iface_oper_status: dict
):

    # transform the CLI data into a measurment instance for consistent
    # comparison with the expected values.

    measurement = EosInterfaceMeasurement.from_cli(iface_oper_status)
    should_oper_status = test_case.expected_results
    if_flags = test_case.test_params.interface_flags or {}
    is_reserved = if_flags.get("is_reserved", False)

    fails = 0

    # -------------------------------------------------------------------------
    # If the interface is marked as reserved, then report the current state in
    # an INFO report and done with this test-case.
    # -------------------------------------------------------------------------

    if is_reserved:
        yield tr.InfoTestCase(
            device=device,
            test_case=test_case,
            field="is_reserved",
            measurement=measurement.dict(),
        )
        return

    # -------------------------------------------------------------------------
    # Check the 'used' status.  Then if the interface is not being used, then no
    # more checks are required.
    # -------------------------------------------------------------------------

    if should_oper_status.used != measurement.used:
        fails += 1
        yield tr.FailFieldMismatchResult(
            device=device,
            test_case=test_case,
            field="used",
            measurement=measurement.used,
        )

    if not should_oper_status.used:
        return

    # -------------------------------------------------------------------------
    # Interface is USED ... check other attributes
    # -------------------------------------------------------------------------

    for field in ("oper_up", "desc", "speed"):

        # if a field is not present in the testcase, then we will skip it. this
        # is true for when `oper_up` is not present when the interface is marked
        # as "is_reserved=True".

        if not (exp_val := getattr(should_oper_status, field)):
            continue

        msrd_val = getattr(measurement, field)

        if exp_val == msrd_val:
            continue

        fails += 1

        yield tr.FailFieldMismatchResult(
            device=device,
            test_case=test_case,
            measurement=msrd_val,
            field=field,
            expected=test_case.expected_results.dict(),
        )

    if fails:
        return

    # -------------------------------------------------------------------------
    # All checks passed
    # -------------------------------------------------------------------------

    yield tr.PassTestCase(
        device=device, test_case=test_case, measurement=measurement.dict()
    )


def eos_test_one_loopback(
    device: Device, test_case: InterfaceTestCase, ifip_oper_status: dict
):
    """
    If the loopback interface exists (previous checked), then no other field
    checks are performed.  Yield this as a passing test-case and record the
    measured values from the device.
    """
    yield tr.PassTestCase(
        device=device, test_case=test_case, measurement=ifip_oper_status
    )


def eos_test_one_svi(
    device: Device, test_case: InterfaceTestCase, svi_oper_status: dict
):
    fails = 0

    # -------------------------------------------------------------------------
    # check the vlan 'name' field, as that should match the test case
    # description field.
    # -------------------------------------------------------------------------

    msrd_name = svi_oper_status["name"]
    expd_desc = test_case.expected_results.desc

    if msrd_name != expd_desc:
        yield tr.FailFieldMismatchResult(
            device=device, test_case=test_case, field="desc", measurement=msrd_name
        )
        fails += 1

    # -------------------------------------------------------------------------
    # check the status field to match it to the expected is operational enabled
    # / disabled value.
    # -------------------------------------------------------------------------

    msrd_status = svi_oper_status["status"]
    expd_status = test_case.expected_results.oper_up

    if expd_status != (msrd_status == "active"):
        yield tr.FailFieldMismatchResult(
            device=device, test_case=test_case, field="oper_up", measurement=msrd_status
        )
        fails += 1

    if fails:
        return

    # -------------------------------------------------------------------------
    # All checks passeed !
    # -------------------------------------------------------------------------

    yield tr.PassTestCase(
        device=device,
        test_case=test_case,
        measurement=test_case.expected_results.dict(),
    )
