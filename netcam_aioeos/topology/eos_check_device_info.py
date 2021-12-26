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
# System Impors
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Impors
# -----------------------------------------------------------------------------

from netcad.topology.check_device_info import DeviceInformationCheckCollection
from netcad.checks import (
    CheckPassResult,
    CheckFailResult,
    CheckInfoLog,
    CheckResultsCollection,
)

# -----------------------------------------------------------------------------
# Private Improts
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from netcam_aioeos.eos_dut import EOSDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_tc_device_info"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def eos_tc_device_info(
    self, testcases: DeviceInformationCheckCollection
) -> CheckResultsCollection:
    dut: EOSDeviceUnderTest = self
    ver_info = dut.version_info
    results = list()

    # check the product model for a match.  The actual product model may be a
    # "front" or "rear" designation.  We'll ignore those for comparison
    # purposes.

    testcase = testcases.checks[0]
    exp_values = testcase.expected_results

    exp_product_model = exp_values.product_model
    has_product_model = ver_info["modelName"]

    if has_product_model[: len(exp_product_model)] == exp_product_model:
        results.append(
            CheckPassResult(
                device=dut.device,
                check=testcase,
                measurement=has_product_model,
                field="product_model",
            )
        )
    else:
        results.append(
            CheckFailResult(
                device=dut.device,
                check=testcase,
                measurement=has_product_model,
                field="product_model",
                error=f"Mismatch: product_model, expected {exp_product_model}, actual {has_product_model}",
            )
        )

    # include an information block that provides the raw "show version" object content.

    results.append(
        CheckInfoLog(
            device=dut.device, check=testcase, field="version", measurement=ver_info
        )
    )

    return results
