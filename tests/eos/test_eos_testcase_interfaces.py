# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

import json
from unittest.mock import AsyncMock, Mock, PropertyMock
from pathlib import Path

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import pytest

from netcad.device import Device
from netcad.checks import TestCasePass
from netcad.topology import interfaces as if_tests


# -----------------------------------------------------------------------------
#
#                               TEST CODE BEGINS
#
# -----------------------------------------------------------------------------


@pytest.fixture()
async def mock_device():
    dev = Mock(spec=Device)
    dev.name = "mock-eos-device"
    return dev


PAYLOADS_DIR = Path(__file__).parent / "payloads"
TESTCASES_DIR = Path(__file__).parent / "testcases"


@pytest.mark.asyncio
async def test_eos_pass_testcases_interface(mock_device: Device):
    """
    This test case validates a "passing" interface whereby the measured values
    match the test-case expected values.
    """

    from netcam_aio_devices.eos.eos_tc_interfaces import (
        eos_test_one_interface,
    )

    if_name = "Ethernet3"

    test_case = if_tests.InterfaceCheck(
        check_params=if_tests.InterfaceCheckParams(interface=if_name),
        expected_results=if_tests.InterfaceCheckUsedExpectations(
            used=True, desc="sw2112-et49/50", speed=10_000, oper_up=True
        ),
    )

    payload_file = PAYLOADS_DIR / "eos_show_interfaces_status.json"
    payload_data = json.load(payload_file.open())

    results = list(
        eos_test_one_interface(
            device=mock_device,
            test_case=test_case,
            iface_oper_status=payload_data["interfaceStatuses"][if_name],
        )
    )

    # There shuold be only 1 result of "pass"

    assert len(results) == 1
    assert isinstance(results[0], TestCasePass)


@pytest.mark.asyncio
async def test_dispatch_eos_testcases_interfaces(mock_device, monkeypatch):
    """
    This purpose of tc_cls_exec test is to ensure that the mechanism of the
    "singledispatchmethod" is working as expected.
    """

    from netcad.topology.interfaces import InterfaceTestCases
    from netcam_aio_devices.eos.eos_dut import DeviceUnderTestEOS

    # noinspection PyTypeChecker
    dut = DeviceUnderTestEOS(device=mock_device, testcases_dir=TESTCASES_DIR)

    # -------------------------------------------------------------------------
    # create a PropertyMock because the way the singledispatchmethod works uses
    # descriptors.  Declare `fake_meth` which will be used to identify whether
    # or the the expected method is called through the dispatch mechanism. The
    # instance of the singledispatchmethod is stored in the class dictionary; se
    # we pull this out of __dict__.  We then need to "patch" the registry entry
    # for the "interfaces" method with the fake_meth.  Since the actual registry
    # is a mappingproxy we cannot write to it directly, so make a dict copy.
    # -------------------------------------------------------------------------

    fake_meth = PropertyMock()
    tc_cls_exec = DeviceUnderTestEOS.__dict__["execute_testcases"]

    registry = dict(tc_cls_exec.dispatcher.registry)
    registry[InterfaceTestCases] = fake_meth

    def fake_dispatch(cls):
        return registry[cls]

    monkeypatch.setattr(
        tc_cls_exec.dispatcher, "dispatch", Mock(side_effect=fake_dispatch)
    )

    # -----[ monkeypatch on singledispatchmethod completed ]-------------------

    # Now execute the "interfaces" testcases as would normally be performed via
    # the "netcam test ..." command.

    payload_file = PAYLOADS_DIR / "eos_show_interfaces_status.json"
    payload_data = json.load(payload_file.open())
    dut.eapi.cli = AsyncMock(return_value=payload_data)

    if_testcases = await InterfaceTestCases.load(testcase_dir=TESTCASES_DIR)

    # nothing should actually be return since this call does not invoke the
    # actual method implementing the tests; the fake_meth should be called
    # however as a result of the above monkeypatch.

    async for _ in dut.execute_device_checks(if_testcases):
        pass

    # check that the fake method mocking the "interface" method was invoked
    # through the dispatching mechanism.

    assert fake_meth.called


# @pytest.mark.asyncio
# async def test_dispatch_eos_testcases_interfaces(mock_device, monkeypatch):
#     """
#     This purpose of tc_cls_exec test is to ensure that the mechanism of the
#     "singledispatchmethod" is working as expected.
#     """
#
#     from netcad.testing_services.interfaces import InterfaceTestCases
#     from netcam_aio_devices.eos.eos_device import DeviceUnderTestEOS
#     from netcam_aio_devices.eos import eos_device
#
#     fake_meth = AsyncMock()
#     monkeypatch.setattr(eos_device, 'eos_testcases_interfaces', fake_meth)
#
#     breakpoint()
#
#     # noinspection PyTypeChecker
#     dut = DeviceUnderTestEOS(device=mock_device, testcases_dir=TESTCASES_DIR)
#
#     # Now execute the "interfaces" testcases as would normally be performed via
#     # the "netcam test ..." command.
#
#     payload_file = PAYLOADS_DIR / "eos_show_interfaces_status.json"
#     payload_data = json.load(payload_file.open())
#     dut.eapi.cli = AsyncMock(return_value=payload_data)
#
#     if_testcases = await InterfaceTestCases.load(testcase_dir=TESTCASES_DIR)
#
#     # nothing should actually be return since this call does not invoke the
#     # actual method implementing the tests; the fake_meth should be called
#     # however as a result of the above monkeypatch.
#
#     async for _ in dut.execute_testcases(if_testcases):
#         pass
#
#     # check that the fake method mocking the "interface" method was invoked
#     # through the dispatching mechanism.
#
#     assert fake_meth.called
