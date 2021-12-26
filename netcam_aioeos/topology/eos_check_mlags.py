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

from typing import TYPE_CHECKING, AsyncGenerator, Generator
import re

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from pydantic import BaseModel

from netcad.topology.check_mlags import (
    MLagCheckCollection,
    MLagSystemCheckParams,
    MLagSystemCheck,
)
from netcad.topology.check_lags import LagCheck
from netcad.device import Device
from netcad.checks import check_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from netcam_aioeos.eos_dut import EOSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_check_mlags", "eos_test_one_mlag"]

_re_mlag_id = re.compile(r"Port-Channel(\d+)")


async def eos_check_mlags(self, testcases: MLagCheckCollection) -> AsyncGenerator:
    """
    This check-executor validates the operational status of the MLAGs running on
    the device against the expected values in the design.
    """

    dut: EOSDeviceUnderTest = self
    device = dut.device

    yield await eos_test_mlag_system_status(dut)

    cli_mlagifs_resp = await dut.eapi.cli("show mlag interfaces")

    # The EOS data is a dictionary key is MLAG ID in string form.

    dev_mlags_data = cli_mlagifs_resp["interfaces"]

    for check in testcases.checks:
        # The test-case ID is the port-channel interface name

        # TODO: for now, need to change the test-case generated to be the MLAG
        #       ID value, not the port-channel interface name.

        mlag_id = _re_mlag_id.match(check.check_id()).group(1)

        if not (mlag_data := dev_mlags_data.get(mlag_id)):
            yield trt.CheckFailNoExists(device=device, check=check)
            continue

        for result in eos_test_one_mlag(
            device=device, check=check, mlag_status=mlag_data
        ):
            yield result


async def eos_test_mlag_system_status(dut: "EOSDeviceUnderTest"):
    """
    This check executes the MLAG configuration santify check and reports any
    failures.
    """

    cli_mlagst_rsp = await dut.eapi.cli("show mlag config-sanity")

    test_case = MLagSystemCheck(
        check_params=MLagSystemCheckParams(), expected_results=BaseModel()
    )

    if all(
        (
            cli_mlagst_rsp["mlagConnected"] is True,
            cli_mlagst_rsp["mlagActive"] is True,
            len(cli_mlagst_rsp["interfaceConfiguration"]) == 0,
            len(cli_mlagst_rsp["globalConfiguration"]) == 0,
        )
    ):
        return trt.CheckPassResult(device=dut.device, check=test_case, measurement="OK")

    return trt.CheckFailFieldMismatch(
        device=dut.device,
        check=test_case,
        field="mlag_status",
        measurement=cli_mlagst_rsp,
        expected={},
    )


def eos_test_one_mlag(device: Device, check: LagCheck, mlag_status: dict) -> Generator:
    """
    This check validates the status of a specific MLAG interface against the
    expected values in the design.
    """

    fails = 0

    # -------------------------------------------------------------------------
    # ensure that the MLAG status is showing a positive value
    # -------------------------------------------------------------------------

    expd_status = "active-full"
    if (msrd_status := mlag_status["status"]) != expd_status:
        yield trt.CheckFailFieldMismatch(
            device=device,
            check=check,
            field="status",
            measurement=msrd_status,
            expected=expd_status,
        )
        fails += 1

    # -------------------------------------------------------------------------
    # ensure the MLAG contains the designated interfaces
    # -------------------------------------------------------------------------

    expd_interfaces = sorted(
        (member.interface for member in check.expected_results.interfaces)
    )
    msrd_interfaces = sorted(
        (mlag_status["localInterface"], mlag_status["peerInterface"])
    )

    if expd_interfaces != msrd_interfaces:
        yield trt.CheckFailFieldMismatch(
            device=device,
            check=check,
            field="interfaces",
            expected=expd_interfaces,
            measurement=msrd_interfaces,
        )
        fails += 1

    if fails:
        return

    # -------------------------------------------------------------------------
    # Test case passed
    # -------------------------------------------------------------------------

    yield trt.CheckPassResult(device=device, check=check, measurement=msrd_interfaces)
