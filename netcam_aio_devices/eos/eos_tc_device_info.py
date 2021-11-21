# -----------------------------------------------------------------------------
# System Impors
# -----------------------------------------------------------------------------

from typing import TYPE_CHECKING

# -----------------------------------------------------------------------------
# Public Impors
# -----------------------------------------------------------------------------

from netcad.testing_services.device import DeviceInformationTestCases
from netcad.netcam import TestCasePass, TestCaseFailed, TestCaseInfo

# -----------------------------------------------------------------------------
# Private Improts
# -----------------------------------------------------------------------------

if TYPE_CHECKING:
    from .eos_dut import DeviceUnderTestEOS

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_tc_device_info"]

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


async def eos_tc_device_info(self, testcases: DeviceInformationTestCases):
    dut: DeviceUnderTestEOS = self
    ver_info = dut.version_info

    # check the product model for a match.  The actual product model may be a
    # "front" or "rear" designation.  We'll ignore those for comparison
    # purposes.

    testcase = testcases.tests[0]
    exp_values = testcase.expected_results

    exp_product_model = exp_values.product_model
    has_product_model = ver_info["modelName"]

    if has_product_model[: len(exp_product_model)] == exp_product_model:
        result = TestCasePass(
            device=dut.device,
            test_case=testcase,
            measurement=has_product_model,
            field="product_model",
        )
    else:
        result = TestCaseFailed(
            device=dut.device,
            test_case=testcase,
            measurement=has_product_model,
            field="product_model",
            error=f"Mismatch: product_model, expected {exp_product_model}, actual {has_product_model}",
        )

    yield result

    # include an information block that provides the raw "show version" object content.

    yield TestCaseInfo(
        device=dut.device, test_case=testcase, field="version", measurement=ver_info
    )
