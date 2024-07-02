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
from typing import Set
from itertools import chain

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.device import Device, DeviceInterface
from netcad.checks import CheckResultsCollection, CheckStatus

from netcad.feats.topology.checks.check_interfaces import (
    InterfaceCheckCollection,
    InterfaceExclusiveListCheck,
    InterfaceExclusiveListCheckResult,
    InterfaceCheck,
    InterfaceCheckResult,
    InterfaceCheckMeasurement,
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


@EOSDeviceUnderTest.execute_checks.register  # noqa
async def eos_check_interfaces(
    self, collection: InterfaceCheckCollection
) -> CheckResultsCollection:
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
        eos_check_exclusive_interfaces_list(
            device=device,
            expd_interfaces=set(check.check_id() for check in collection.checks),
            msrd_interfaces=set(chain(map_if_oper_data, map_ip_ifaces)),
            results=results,
        )

    # -------------------------------------------------------------------------
    # Check each interface for health checks
    # -------------------------------------------------------------------------

    for check in collection.checks:
        if_name = check.check_id()

        # ---------------------------------------------------------------------
        # if the interface is an SVI, that it begins with "Vlan", then we need
        # to examine it differently since it does not show up in the "show
        # interfaces ..." command.
        # ---------------------------------------------------------------------

        if vlan_mo := _match_svi(if_name):
            # extract the VLAN ID value from the interface name; the lookup is
            # an int-as-string since that is how the data is encoded in the CLI
            # response object.  If the VLAN does not exist, or if the VLAN does
            # exist but there is no Cpu interface, then the "interface Vlan<N>"
            # does not exist on the device.

            vlan_id = vlan_mo.group(1)

            eos_check_one_svi(
                device=device,
                check=check,
                svi_oper_status=map_svi_oper_data.get(vlan_id),
                results=results,
            )

            # done with Vlan interface, go to next test-case
            continue

        # ---------------------------------------------------------------------
        # If the interface is a Loopback ...
        # ---------------------------------------------------------------------

        if if_name.startswith("Loopback"):
            result = InterfaceCheckResult(device=device, check=check)

            if not (lo_status := map_ip_ifaces.get(if_name)):
                result.measurement = None
                results.append(result.measure())
                continue

            # if the loopback exists, then it is a PASS, and we are not going
            # to check anything else at this time.
            result.measurement.oper_up = lo_status['lineProtocolStatus'] == 'up'
            results.append(result)

            # done with Loopback, go to next test-case
            continue

        # ---------------------------------------------------------------------
        # If here, then standard interface check
        # ---------------------------------------------------------------------

        eos_check_one_interface(
            device=device,
            check=check,
            iface_oper_status=map_if_oper_data.get(if_name),
            results=results,
        )

    return results


# -----------------------------------------------------------------------------
#
#                       PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def eos_check_exclusive_interfaces_list(
    device: Device,
    expd_interfaces: Set[str],
    msrd_interfaces: Set[str],
    results: CheckResultsCollection,
):
    """
    This check validates the exclusive list of interfaces found on the device
    against the expected list in the design.
    """

    def sort_key(i):
        return DeviceInterface(i, interfaces=device.interfaces)

    check = InterfaceExclusiveListCheck(
        expected_results=sorted(expd_interfaces, key=sort_key)
    )

    result = InterfaceExclusiveListCheckResult(
        device=device, check=check, measurement=sorted(msrd_interfaces, key=sort_key)
    )

    results.append(result.measure(sort_key=sort_key))


# -----------------------------------------------------------------------------
# EOS Measurement dataclass
# -----------------------------------------------------------------------------

BITS_TO_MBS = 10**-6


class EosInterfaceMeasurement(InterfaceCheckMeasurement):
    """
    This dataclass is used to store the values as retrieved from the EOS device
    into a set of attributes that align to the test-case.
    """

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
    device: Device,
    check: InterfaceCheck,
    iface_oper_status: dict,
    results: CheckResultsCollection,
):
    """
    Validates a specific physical interface against the expectations in the
    design.
    """
    result = InterfaceCheckResult(device=device, check=check)

    # if the interface does not exist, then no further checking.

    if not iface_oper_status:
        result.measurement = None
        results.append(result.measure())
        return

    # transform the CLI data into a measurment instance for consistent
    # comparison with the expected values.

    measurement = EosInterfaceMeasurement.from_cli(iface_oper_status)

    if_flags = check.check_params.interface_flags or {}
    is_reserved = if_flags.get("is_reserved", False)

    # -------------------------------------------------------------------------
    # If the interface is marked as reserved, then report the current state in
    # an INFO report and done with this test-case.
    # -------------------------------------------------------------------------

    if is_reserved:
        result.status = CheckStatus.INFO
        result.logs.INFO("reserved", measurement.dict())
        results.append(result.measure())
        return results

    # override the expected condition if there is a forced unused on a port
    if is_forced_unused := if_flags.get("is_forced_unused"):
        check.expected_results.used = False

    # -------------------------------------------------------------------------
    # Check the 'used' status.  Then if the interface is not being used, then no
    # more checks are required.
    # -------------------------------------------------------------------------

    result.measurement = measurement

    def on_mismatch(_field, _expected, _measured) -> CheckStatus:
        # if the field is description, then it is a warning, and not a failure.
        if _field == "desc":

            # if the design is meant to force a shutdown on the port, then we
            # really do want to surface the description error.

            if is_forced_unused:
                return CheckStatus.FAIL

            # otherwise, the description mismatch is just a warning.
            return CheckStatus.WARN

        # if the speed is mismatched because the port is down, then this is not
        # a failure.
        if _field == "speed" and measurement.oper_up is False:
            return CheckStatus.SKIP

    results.append(result.measure(on_mismatch=on_mismatch))
    return


def eos_check_one_svi(
    device: Device,
    check: InterfaceCheck,
    svi_oper_status: dict | None,
    results: CheckResultsCollection,
):
    """
    Checks the device state for a VLAN SVI interface against the expected
    values in the design.
    """

    result = InterfaceCheckResult(device=device, check=check)

    if not svi_oper_status:
        result.measurement = None

    elif not (svi_oper_status or "Cpu" not in svi_oper_status["interfaces"]):
        result.measurement = None

    else:
        msrd = result.measurement
        msrd.used = True
        msrd.desc = check.expected_results.desc
        msrd.oper_up = svi_oper_status["status"] == "active"

    results.append(result.measure())
