import json
from unittest.mock import AsyncMock
from pathlib import Path

import pytest

from netcad.testing_services import TestCasePass, interfaces as if_tests

from netcam_aio_devices.eos import Device
from netcam_aio_devices.eos.testing_services.eos_test_interfaces import (
    eos_test_one_interface,
)


@pytest.mark.asyncio
@pytest.fixture()
async def mock_device():
    dev = AsyncMock(spec=Device)
    dev.host = "mock-eos-device"
    return dev


@pytest.fixture()
def paylaod_dir():
    return Path(__file__).parent / "payloads"


@pytest.mark.asyncio
async def test_eos_pass_testcases_interface(mock_device: Device, paylaod_dir):

    if_name = "Ethernet3"

    test_case = if_tests.InterfaceTestCase(
        test_params=if_tests.InterfaceTestParams(interface=if_name),
        expected_results=if_tests.InterfaceTestUsedExpectations(
            used=True, desc="sw2112-et49/50", speed=10_000, oper_up=True
        ),
    )

    payload_file = paylaod_dir / "eos_show_interfaces_status.json"
    payload_data = json.load(payload_file.open())

    results = list(
        eos_test_one_interface(
            device=mock_device,
            test_case=test_case,
            iface_oper_status=payload_data["interfaceStatuses"][if_name],
        )
    )

    assert all((isinstance(result, TestCasePass) for result in results))
