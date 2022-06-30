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

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Set

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------
from netcad.checks import CheckResultsCollection, CheckStatus

from netcad.topology.checks.check_transceivers import (
    TransceiverCheckCollection,
    TransceiverCheckResult,
    TransceiverExclusiveListCheck,
    TransceiverExclusiveListCheckResult,
)
from netcad.topology import transceiver_model_matches, transceiver_type_matches
from netcad.device import Device, DeviceInterface

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_check_transceivers"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


@EOSDeviceUnderTest.execute_checks.register
async def eos_check_transceivers(
    dut, check_collection: TransceiverCheckCollection
) -> CheckResultsCollection:
    """
    This method is imported into the ESO DUT class definition to support
    checking the status of the transceivers.

    Notes
    -----
    On EOS platforms, the XCVR inventory is stored as port _numbers-strings_ and
    not as the interface name.  For example, "Interface54/1" is represented in
    the EOS inventor as "54".
    """

    dut: EOSDeviceUnderTest
    device = dut.device

    # obtain the transceiver _model_ information from the inventory command.

    cli_xcvrinv_resp_data = await dut.eapi.cli("show inventory")
    dev_inv_ifstatus = cli_xcvrinv_resp_data["xcvrSlots"]

    # obtain the transceiver _type_ information from the interfaces command.
    # This payload has structure: .interfaces.<interface-name> = {}

    cli_ifs_resp_data = await dut.eapi.cli("show interfaces hardware")
    dev_ifhw_ifstatus = cli_ifs_resp_data["interfaces"]

    # keep a set of the interface port numbers defined in the test cases so that
    # we can match that against the exclusive list vs. the transceivers in the
    # inventory.

    if_port_numbers = set()

    results = list()

    # first run through each of the per interface test cases ensuring that the
    # expected transceiver type and model are present.  While doing this keep
    # track of the interfaces port-numbers so that we can compare them to the
    # eclusive list.

    rsvd_ports_set = set()

    for check in check_collection.checks:
        result = TransceiverCheckResult(device=device, check=check)

        if_name = check.check_id()
        dev_iface: DeviceInterface = device.interfaces[if_name]

        if_pri_port = dev_iface.port_numbers[0]
        ifaceinv = (dev_inv_ifstatus.get(str(if_pri_port)),)
        ifacehw = (dev_ifhw_ifstatus.get(if_name),)

        if dev_iface.profile.is_reserved:
            result.status = CheckStatus.INFO
            result.logs.INFO(
                "reserved",
                dict(
                    message="interface is in reserved state",
                    hardware=ifaceinv,  # from the show inventory command
                    status=ifacehw,  # from the show interfaces ... hardware command
                ),
            )
            results.append(result.measure())
            rsvd_ports_set.add(if_pri_port)
            continue

        if_port_numbers.add(if_pri_port)

        eos_test_one_interface(
            result=result,
            ifaceinv=dev_inv_ifstatus.get(str(if_pri_port)),
            ifacehw=dev_ifhw_ifstatus.get(if_name),
            results=results,
        )

    # next add the test coverage for the exclusive list.

    if check_collection.exclusive:
        _check_exclusive_list(
            device=device,
            expd_ports=if_port_numbers,
            msrd_ports=dev_inv_ifstatus,
            rsvd_ports=rsvd_ports_set,
            results=results,
        )

    return results


# -----------------------------------------------------------------------------
#
#                            PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def _check_exclusive_list(
    device: Device,
    expd_ports,
    msrd_ports,
    rsvd_ports: Set,
    results: CheckResultsCollection,
):
    """
    Check to ensure that the list of transceivers found on the device matches the exclusive list.
    This check helps to find "unused" optics; or report them so that a Designer can account for them
    in the design-notes.
    """

    check = TransceiverExclusiveListCheck(expected_results=expd_ports)

    used_msrd_ports = {
        int(po_num)
        for po_num, po_data in msrd_ports.items()
        if po_data.get("modelName")
    }

    # remove the reserved ports form the used list so that we do not consider
    # them as part of the exclusive list testing.

    used_msrd_ports -= rsvd_ports

    result = TransceiverExclusiveListCheckResult(
        device=device, check=check, measurement=used_msrd_ports
    )

    results.append(result.measure())


def eos_test_one_interface(
    ifaceinv: dict,
    ifacehw: dict,
    result: TransceiverCheckResult,
    results: CheckResultsCollection,
):
    """
    This function validates that a specific interface is using the specific
    transceiver as defined in the design.
    """

    # if there is no entry for this interface, then the transceiver does not
    # exist.  if there is no model value, then the transceiver does not exist.

    if not ifaceinv or not ifaceinv.get("modelName"):
        result.measurement = None
        results.append(result.measure())
        return

    msrd = result.measurement
    msrd.model = ifaceinv["modelName"]
    msrd.type = ifacehw["transceiverType"]

    def on_mismatch(_field, _expd, _msrd):
        match _field:
            case "model":
                is_ok = transceiver_model_matches(
                    expected_model=_expd, given_mdoel=_msrd
                )
            case "type":
                is_ok = transceiver_type_matches(expected_type=_expd, given_type=_msrd)
            case _:
                is_ok = False

        return CheckStatus.PASS if is_ok else CheckStatus.FAIL

    results.append(result.measure(on_mismatch=on_mismatch))
