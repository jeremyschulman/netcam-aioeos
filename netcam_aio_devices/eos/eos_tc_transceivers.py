# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.testing_services.transceivers import (
    TransceiverTestCases,
    TransceiverTestCase,
)

from netcad.device import Device, DeviceInterface
from netcad.netcam import tc_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from netcam_aio_devices.eos import DeviceUnderTestEOS

from .eos_xcvr_matching import eos_xcvr_model_matches, eos_xcvr_type_matches

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_test_transceivers"]


async def eos_test_transceivers(self, testcases: TransceiverTestCases):
    """
    This method is imported into the ESO DUT class definition to support
    checking the status of the transceivers.

    Notes
    -----
    On EOS platforms, the XCVR inventory is stored as port _numbers-strings_ and
    not as the interface name.  For example, "Interface54/1" is represented in
    the EOS inventor as "54".
    """

    # noinspection PyTypeChecker
    dut: DeviceUnderTestEOS = self
    device = dut.device

    # obtain the transceiver _model_ information from the inventory command.

    cli_xcvrinv_resp_data = await dut.eapi.cli("show inventory")
    dev_inv_ifstatus = cli_xcvrinv_resp_data["xcvrSlots"]

    # obtain the transceiver _type_ information from the interfaces command.
    # This payload has structure: .interfaces.<interface-name> = {}

    cli_ifs_resp_data = await dut.eapi.cli("show interfaces hardware")
    dev_ifhw_ifstatus = cli_ifs_resp_data["interfaces"]

    for each_test in testcases.tests:

        if_name = each_test.test_case_id()
        dev_iface: DeviceInterface = device.interfaces[if_name]
        if_pri_port = dev_iface.port_numbers[0]

        for result in eos_test_one_interface(
            device=device,
            test_case=each_test,
            ifaceinv=dev_inv_ifstatus.get(str(if_pri_port)),
            ifacehw=dev_ifhw_ifstatus.get(if_name),
        ):
            yield result


def eos_test_one_interface(
    device: Device, test_case: TransceiverTestCase, ifaceinv: dict, ifacehw: dict
):

    if not ifaceinv:
        yield trt.FailNoExistsTestCase(
            device=device,
            test_case=test_case,
        )
        return

    failed = 0

    exp_model = test_case.expected_results.model
    msrd_model = ifaceinv["modelName"]
    if not eos_xcvr_model_matches(exp_model, msrd_model):
        yield trt.FailTestCaseOnField(
            device=device, test_case=test_case, field="model", measurement=msrd_model
        )
        failed += 1

    expd_type = test_case.expected_results.type
    msrd_type = ifacehw["transceiverType"]
    if not eos_xcvr_type_matches(expd_type, msrd_type):
        yield trt.FailTestCaseOnField(
            device=device, test_case=test_case, field="type", measurement=msrd_type
        )
        failed += 1

    if failed:
        return

    # -------------------------------------------------------------------------
    # Test Case Passes, provide info data as well.
    # -------------------------------------------------------------------------

    yield trt.TestCasePass(
        device=device,
        test_case=test_case,
        measurement=dict(model=msrd_model, type=msrd_type),
    )


# def eos_test_one_interface(
#     device: Device, test_case: TransceiverTestCase, ifoper_status: dict
# ):
#     if not ifoper_status:
#         yield trt.FailNoExistsTestCase(
#             device=device,
#             test_case=test_case,
#         )
#         return
#
#     xcvr_type = ifoper_status['transceiverType']
#
#     if xcvr_type != test_case.expected_results.model:
#         yield trt.FailTestCaseOnField(
#             device=device,
#             test_case=test_case,
#             field='model',
#             measurement=xcvr_type
#         )
#     else:
#         yield trt.TestCasePass(
#             device=device,
#             test_case=test_case,
#             measurement=xcvr_type
#         )
