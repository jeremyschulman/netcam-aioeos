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
# Public Impors
# -----------------------------------------------------------------------------

from netcad.topology.checks.check_device_info import DeviceInformationCheckCollection
from netcad.checks import (
    CheckPassResult,
    CheckFailResult,
    CheckInfoLog,
    CheckResultsCollection,
)

# -----------------------------------------------------------------------------
# Private Improts
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest

# -----------------------------------------------------------------------------
# Exports (None)
# -----------------------------------------------------------------------------

__all__ = ()

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


@EOSDeviceUnderTest.execute_checks.register
async def eos_check_device_info(
    self, device_checks: DeviceInformationCheckCollection
) -> CheckResultsCollection:
    """
    The check executor to validate the device information.  Presently this
    function validates the product-model value.  It also captures the results
    of the 'show version' into a check-inforamation.
    """
    dut: EOSDeviceUnderTest = self
    ver_info = dut.version_info
    results = list()

    # check the product model for a match.  The actual product model may be a
    # "front" or "rear" designation.  We'll ignore those for comparison
    # purposes.

    check = device_checks.checks[0]
    exp_values = check.expected_results

    exp_product_model = exp_values.product_model
    has_product_model = ver_info["modelName"]

    check_len = min(len(has_product_model), len(exp_product_model))
    match = has_product_model[:check_len] == exp_product_model[:check_len]

    if match:
        results.append(
            CheckPassResult(
                device=dut.device,
                check=check,
                measurement=has_product_model,
                field="product_model",
            )
        )
    else:
        results.append(
            CheckFailResult(
                device=dut.device,
                check=check,
                measurement=has_product_model,
                field="product_model",
                error=f"Mismatch: product_model, expected {exp_product_model}, actual {has_product_model}",
            )
        )

    # include an information block that provides the raw "show version" object content.

    results.append(
        CheckInfoLog(
            device=dut.device, check=check, field="version", measurement=ver_info
        )
    )

    return results
