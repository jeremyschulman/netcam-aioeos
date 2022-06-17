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

from netcad.topology.checks.check_transceivers import (
    TransceiverCheckCollection,
    TransceiverCheck,
    TransceiverCheckExclusiveList,
)
from netcad.topology import transceiver_model_matches, transceiver_type_matches

from netcad.device import Device, DeviceInterface
from netcad.netcam import any_failures
from netcad.checks import check_result_types as trt

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
    self, check_collection: TransceiverCheckCollection
) -> trt.CheckResultsCollection:
    """
    This method is imported into the ESO DUT class definition to support
    checking the status of the transceivers.

    Notes
    -----
    On EOS platforms, the XCVR inventory is stored as port _numbers-strings_ and
    not as the interface name.  For example, "Interface54/1" is represented in
    the EOS inventor as "54".
    """

    dut: EOSDeviceUnderTest = self
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

        if_name = check.check_id()
        dev_iface: DeviceInterface = device.interfaces[if_name]

        if_pri_port = dev_iface.port_numbers[0]
        ifaceinv = (dev_inv_ifstatus.get(str(if_pri_port)),)
        ifacehw = (dev_ifhw_ifstatus.get(if_name),)

        if dev_iface.profile.is_reserved:
            results.append(
                trt.CheckInfoLog(
                    device=device,
                    check=check,
                    measurement=dict(
                        message="interface is in reserved state",
                        hardware=ifaceinv,  # from the show inventory command
                        status=ifacehw,  # from the show interfaces ... hardware command
                    ),
                )
            )
            rsvd_ports_set.add(if_pri_port)
            continue

        if_port_numbers.add(if_pri_port)

        results.extend(
            eos_test_one_interface(
                device=device,
                check=check,
                ifaceinv=dev_inv_ifstatus.get(str(if_pri_port)),
                ifacehw=dev_ifhw_ifstatus.get(if_name),
            )
        )

    # next add the test coverage for the exclusive list.
    if check_collection.exclusive:
        results.extend(
            eos_test_exclusive_list(
                device=device,
                expd_ports=if_port_numbers,
                msrd_ports=dev_inv_ifstatus,
                rsvd_ports=rsvd_ports_set,
            )
        )

    return results


# -----------------------------------------------------------------------------
#
#                            PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def eos_test_exclusive_list(
    device: Device, expd_ports, msrd_ports, rsvd_ports: Set
) -> trt.CheckResultsCollection:
    """
    Check to ensure that the list of transceivers found on the device matches the exclusive list.
    This check helps to find "unused" optics; or report them so that a Designer can account for them
    in the design-notes.
    """

    results = list()
    tc = TransceiverCheckExclusiveList()

    used_msrd_ports = {
        int(po_num)
        for po_num, po_data in msrd_ports.items()
        if po_data.get("modelName")
    }

    # remove the reserved ports form the used list so that we do not consider
    # them as part of the exclusive list testing.

    used_msrd_ports -= rsvd_ports

    if missing := expd_ports - used_msrd_ports:
        results.append(
            trt.CheckFailMissingMembers(
                device=device,
                check=tc,
                field="transceivers",
                expected=sorted(expd_ports),
                missing=sorted(missing),
            )
        )

    if extras := used_msrd_ports - expd_ports:
        results.append(
            trt.CheckFailExtraMembers(
                device=device,
                check=tc,
                field="transceivers",
                expected=sorted(expd_ports),
                extras=sorted(extras),
            )
        )

    if not any_failures(results):
        results.append(
            trt.CheckPassResult(
                device=device,
                check=TransceiverCheckExclusiveList(),
                measurement="OK: no extra or missing transceivers",
            )
        )

    return results


def eos_test_one_interface(
    device: Device, check: TransceiverCheck, ifaceinv: dict, ifacehw: dict
) -> trt.CheckResultsCollection:
    """
    This function validates that a specific interface is using the specific
    transceiver as defined in the design.
    """

    results = list()

    # if there is no entry for this interface, then the transceiver does not
    # exist.

    if not ifaceinv:
        results.append(
            trt.CheckFailNoExists(
                device=device,
                check=check,
            )
        )
        return results

    # if there is no model value, then the transceiver does not exist.

    exp_model = check.expected_results.model
    if not (msrd_model := ifaceinv["modelName"]):
        results.append(
            trt.CheckFailNoExists(
                device=device,
                check=check,
            )
        )
        return results

    if not transceiver_model_matches(expected_model=exp_model, given_mdoel=msrd_model):
        results.append(
            trt.CheckFailFieldMismatch(
                device=device,
                check=check,
                field="model",
                measurement=msrd_model,
            )
        )

    expd_type = check.expected_results.type
    msrd_type = ifacehw["transceiverType"]
    if not transceiver_type_matches(expected_type=expd_type, given_type=msrd_type):
        results.append(
            trt.CheckFailFieldMismatch(
                device=device, check=check, field="type", measurement=msrd_type
            )
        )

    if not any_failures(results):
        results.append(
            trt.CheckPassResult(
                device=device,
                check=check,
                measurement=dict(model=msrd_model, type=msrd_type),
            )
        )

    return results
