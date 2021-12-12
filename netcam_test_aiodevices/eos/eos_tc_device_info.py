# -----------------------------------------------------------------------------
# System Impors
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Impors
# -----------------------------------------------------------------------------

from netcad.topology.tc_device_info import DeviceInformationTestCases
from netcad.netcam import (
    PassTestCase,
    FailTestCase,
    InfoTestCase,
    CollectionTestResults,
)

# -----------------------------------------------------------------------------
# Private Improts
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .eos_dut import EOSDeviceUnderTest

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
    self, testcases: DeviceInformationTestCases
) -> CollectionTestResults:
    dut: EOSDeviceUnderTest = self
    ver_info = dut.version_info
    results = list()

    # check the product model for a match.  The actual product model may be a
    # "front" or "rear" designation.  We'll ignore those for comparison
    # purposes.

    testcase = testcases.tests[0]
    exp_values = testcase.expected_results

    exp_product_model = exp_values.product_model
    has_product_model = ver_info["modelName"]

    if has_product_model[: len(exp_product_model)] == exp_product_model:
        results.append(
            PassTestCase(
                device=dut.device,
                test_case=testcase,
                measurement=has_product_model,
                field="product_model",
            )
        )
    else:
        results.append(
            FailTestCase(
                device=dut.device,
                test_case=testcase,
                measurement=has_product_model,
                field="product_model",
                error=f"Mismatch: product_model, expected {exp_product_model}, actual {has_product_model}",
            )
        )

    # include an information block that provides the raw "show version" object content.

    results.append(
        InfoTestCase(
            device=dut.device, test_case=testcase, field="version", measurement=ver_info
        )
    )

    return results
