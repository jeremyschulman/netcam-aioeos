# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.topology.tc_transceivers import (
    TransceiverTestCases,
    TransceiverTestCase,
    TransceiverListTestCase,
)

from netcad.device import Device, DeviceInterface
from netcad.netcam import any_failures, tc_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from netcam_aioeos.eos import EOSDeviceUnderTest

from .eos_xcvr_matching import eos_xcvr_model_matches, eos_xcvr_type_matches

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_test_transceivers"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def eos_test_transceivers(
    self, testcases: TransceiverTestCases
) -> trt.CollectionTestResults:
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

    for each_test in testcases.tests:

        if_name = each_test.test_case_id()
        dev_iface: DeviceInterface = device.interfaces[if_name]
        if_pri_port = dev_iface.port_numbers[0]
        if_port_numbers.add(if_pri_port)

        results.extend(
            eos_test_one_interface(
                device=device,
                test_case=each_test,
                ifaceinv=dev_inv_ifstatus.get(str(if_pri_port)),
                ifacehw=dev_ifhw_ifstatus.get(if_name),
            )
        )

    # next add the test coverage for the exclusive list.

    results.extend(
        eos_test_exclusive_list(
            device=device, expd_ports=if_port_numbers, msrd_ports=dev_inv_ifstatus
        )
    )

    return results


# -----------------------------------------------------------------------------
#
#                            PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def eos_test_exclusive_list(
    device: Device, expd_ports, msrd_ports
) -> trt.CollectionTestResults:

    results = list()
    tc = TransceiverListTestCase()

    used_msrd_ports = {
        int(po_num)
        for po_num, po_data in msrd_ports.items()
        if po_data.get("modelName")
    }

    if missing := expd_ports - used_msrd_ports:
        results.append(
            trt.FailMissingMembersResult(
                device=device,
                test_case=tc,
                field="transceivers",
                expected=sorted(expd_ports),
                missing=sorted(missing),
            )
        )

    if extras := used_msrd_ports - expd_ports:
        results.append(
            trt.FailExtraMembersResult(
                device=device,
                test_case=tc,
                field="transceivers",
                expected=sorted(expd_ports),
                extras=sorted(extras),
            )
        )

    if not any_failures(results):
        results.append(
            trt.PassTestCase(
                device=device,
                test_case=TransceiverListTestCase(),
                measurement="OK: no extra or missing transceivers",
            )
        )

    return results


def eos_test_one_interface(
    device: Device, test_case: TransceiverTestCase, ifaceinv: dict, ifacehw: dict
) -> trt.CollectionTestResults:

    results = list()

    if not ifaceinv:
        results.append(
            trt.FailNoExistsResult(
                device=device,
                test_case=test_case,
            )
        )
        return results

    exp_model = test_case.expected_results.model
    msrd_model = ifaceinv["modelName"]
    if not eos_xcvr_model_matches(exp_model, msrd_model):
        results.append(
            trt.FailFieldMismatchResult(
                device=device,
                test_case=test_case,
                field="model",
                measurement=msrd_model,
            )
        )

    expd_type = test_case.expected_results.type
    msrd_type = ifacehw["transceiverType"]
    if not eos_xcvr_type_matches(expd_type, msrd_type):
        results.append(
            trt.FailFieldMismatchResult(
                device=device, test_case=test_case, field="type", measurement=msrd_type
            )
        )

    if not any_failures(results):
        results.append(
            trt.PassTestCase(
                device=device,
                test_case=test_case,
                measurement=dict(model=msrd_model, type=msrd_type),
            )
        )

    return results
