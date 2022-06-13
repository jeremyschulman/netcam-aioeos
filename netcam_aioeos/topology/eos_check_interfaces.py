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

import re
from typing import Set, List, Iterable
from itertools import chain

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from pydantic import BaseModel

from netcad.device import Device, DeviceInterface
from netcad.netcam import any_failures
from netcad.checks import check_result_types as tr

from netcad.topology.checks.check_interfaces import (
    InterfaceCheckExclusiveList,
    InterfacesListExpected,
    InterfaceCheckCollection,
    InterfaceCheck,
)

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_check_interfaces", "eos_check_one_interface", "eos_check_one_svi"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------

_match_svi = re.compile(r"Vlan(\d+)").match


@EOSDeviceUnderTest.execute_checks.register
async def eos_check_interfaces(
    self, collection: InterfaceCheckCollection
) -> tr.CheckResultsCollection:
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

    collection: InterfaceCheckCollection
        The testcases instance that contains the specific testing details.

    Yields
    ------
    TestCasePass, TestCaseFailed
    """

    dut: EOSDeviceUnderTest = self
    device = dut.device
    results = list()

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

    if collection.exclusive:
        results.extend(
            eos_check_exclusive_interfaces_list(
                device=device,
                expd_interfaces=set(check.check_id() for check in collection.checks),
                msrd_interfaces=set(chain(map_if_oper_data, map_ip_ifaces)),
            )
        )

    # -------------------------------------------------------------------------
    # Check each interface for health checks
    # -------------------------------------------------------------------------

    for check in collection.checks:

        if_name = check.check_id()

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

            if not svi_oper_status:
                results.append(tr.CheckFailNoExists(device=device, check=check))
                continue

            elif not (svi_oper_status or "Cpu" not in svi_oper_status["interfaces"]):
                results.append(tr.CheckFailNoExists(device=device, check=check))
                continue

            results.extend(
                eos_check_one_svi(
                    device=device, check=check, svi_oper_status=svi_oper_status
                )
            )

            # done with Vlan interface, go to next test-case
            continue

        # ---------------------------------------------------------------------
        # If the interface is a Loopback ...
        # ---------------------------------------------------------------------

        if if_name.startswith("Loopback"):
            if not (lo_status := map_ip_ifaces.get(if_name)):
                results.append(tr.CheckFailNoExists(device=device, check=check))
                continue

            results.extend(
                eos_check_one_loopback(
                    device=device, check=check, ifip_oper_status=lo_status
                )
            )

            # done with Loopback, go to next test-case
            continue

        # ---------------------------------------------------------------------
        # The interface is not an SVI, look into the "show interfaces ..."
        # output. if the interface does not exist on the device, then the test
        # fails, and we go onto the next text.
        # ---------------------------------------------------------------------

        if not (iface_oper_status := map_if_oper_data.get(if_name)):
            results.append(tr.CheckFailNoExists(device=device, check=check))

        results.extend(
            eos_check_one_interface(
                device=device,
                check=check,
                iface_oper_status=iface_oper_status,
            )
        )

    return results


# -----------------------------------------------------------------------------
#
#                       PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def sorted_by_name(device: Device, if_name_list: Iterable[str]) -> List[str]:
    return [
        iface.name
        for iface in (
            DeviceInterface(if_name, interfaces=device.interfaces)
            for if_name in if_name_list
        )
    ]


def eos_check_exclusive_interfaces_list(
    device: Device, expd_interfaces: Set[str], msrd_interfaces: Set[str]
) -> tr.CheckResultsCollection:
    """
    This check validates the exclusive list of interfaces found on the device
    against the expected list in the design.
    """

    tc = InterfaceCheckExclusiveList(
        expected_results=InterfacesListExpected(if_name_list=list(expd_interfaces))
    )

    expd_sorted_names = sorted_by_name(device, expd_interfaces)

    results = list()

    if missing_interfaces := expd_interfaces - msrd_interfaces:

        results.append(
            tr.CheckFailMissingMembers(
                device=device,
                check=tc,
                field="interfaces",
                expected=expd_sorted_names,
                missing=sorted_by_name(device, missing_interfaces),
            )
        )

    if extra_interfaces := msrd_interfaces - expd_interfaces:
        results.append(
            tr.CheckFailExtraMembers(
                device=device,
                check=tc,
                field="interfaces",
                expected=expd_sorted_names,
                extras=sorted_by_name(device, extra_interfaces),
            )
        )

    if not any_failures(results):
        results.append(
            tr.CheckPassResult(
                device=device,
                check=tc,
                measurement="OK: no extra or missing interfaces",
            )
        )

    return results


# -----------------------------------------------------------------------------
# EOS Measurement dataclass
# -----------------------------------------------------------------------------

BITS_TO_MBS = 10**-6


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


def eos_check_one_interface(
    device: Device, check: InterfaceCheck, iface_oper_status: dict
) -> tr.CheckResultsCollection:
    """
    Validates a specific physical interface against the expectations in the
    design.
    """

    # transform the CLI data into a measurment instance for consistent
    # comparison with the expected values.

    measurement = EosInterfaceMeasurement.from_cli(iface_oper_status)
    should_oper_status = check.expected_results
    if_flags = check.check_params.interface_flags or {}
    is_reserved = if_flags.get("is_reserved", False)
    results = list()

    # -------------------------------------------------------------------------
    # If the interface is marked as reserved, then report the current state in
    # an INFO report and done with this test-case.
    # -------------------------------------------------------------------------

    if is_reserved:
        results.append(
            tr.CheckInfoLog(
                device=device,
                check=check,
                field="is_reserved",
                measurement=measurement.dict(),
            )
        )
        return results

    # -------------------------------------------------------------------------
    # Check the 'used' status.  Then if the interface is not being used, then no
    # more checks are required.
    # -------------------------------------------------------------------------

    if should_oper_status.used != measurement.used:
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="used",
                measurement=measurement.used,
            )
        )

    if not should_oper_status.used:
        return results

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

        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=check,
                measurement=msrd_val,
                field=field,
                expected=check.expected_results.dict(),
            )
        )

    if not any_failures(results):
        results.append(
            tr.CheckPassResult(
                device=device, check=check, measurement=measurement.dict()
            )
        )

    return results


def eos_check_one_loopback(
    device: Device, check: InterfaceCheck, ifip_oper_status: dict
) -> tr.CheckResultsCollection:
    """
    If the loopback interface exists (previous checked), then no other field
    checks are performed.  Yield this as a passing test-case and record the
    measured values from the device.
    """
    return [
        tr.CheckPassResult(device=device, check=check, measurement=ifip_oper_status)
    ]


def eos_check_one_svi(
    device: Device, check: InterfaceCheck, svi_oper_status: dict
) -> tr.CheckResultsCollection:
    """
    Checks the device state for a VLAN interface against the expected values in
    the design.
    """
    results = list()

    # -------------------------------------------------------------------------
    # check the vlan 'name' field, as that should match the test case
    # description field.
    # -------------------------------------------------------------------------

    msrd_name = svi_oper_status["name"]
    expd_desc = check.expected_results.desc

    if msrd_name != expd_desc:
        results.append(
            tr.CheckFailFieldMismatch(
                device=device, check=check, field="desc", measurement=msrd_name
            )
        )

    # -------------------------------------------------------------------------
    # check the status field to match it to the expected is operational enabled
    # / disabled value.
    # -------------------------------------------------------------------------

    msrd_status = svi_oper_status["status"]
    expd_status = check.expected_results.oper_up

    if expd_status != (msrd_status == "active"):
        results.append(
            tr.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="oper_up",
                measurement=msrd_status,
            )
        )

    # -------------------------------------------------------------------------
    # All checks passeed !
    # -------------------------------------------------------------------------

    if not any_failures(results):
        results.append(
            tr.CheckPassResult(
                device=device,
                check=check,
                measurement=check.expected_results.dict(),
            )
        )

    return results
