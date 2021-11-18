# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from pydantic import BaseModel, PositiveInt
from netcad.testing_services import TestCasePass, TestCaseFailed
from netcad.testing_services.interfaces import InterfaceTestCases, InterfaceTestCase

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aio_devices.eos import Device
from netcam_aio_devices.testing_services import executor_test_interfaces

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_testcases_interfaces", "eos_test_one_interface"]


# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


@executor_test_interfaces.register
async def eos_testcases_interfaces(device: Device, testcases: InterfaceTestCases):
    cli_data = await device.cli("show interfaces status")
    map_if_oper_data: dict = cli_data["interfaceStatuses"]

    for each_test in testcases.tests:
        if_name = each_test.test_case_id()

        for result in eos_test_one_interface(
            device=device,
            test_case=each_test,
            iface_oper_status=map_if_oper_data.get(if_name),
        ):
            yield result


# -----------------------------------------------------------------------------
# EOS Measurement dataclass
# -----------------------------------------------------------------------------

BITS_TO_MBS = 10 ** -6


class EosInterfaceMeasurement(BaseModel):
    """
    This dataclass is used to store the values as retrieved from the EOS device
    into a set of attributes that align to the test-case.
    """

    used: bool
    oper_up: bool
    desc: str
    speed: PositiveInt

    @classmethod
    def from_cli(cls, cli_payload: dict):
        """returns an EOS specific measurement mapping the CLI object fields"""
        return cls(
            used=cli_payload["linkStatus"] != "disabled",
            oper_up=cli_payload["lineProtocolStatus"] == "up",
            desc=cli_payload["description"],
            speed=cli_payload["bandwidth"] * BITS_TO_MBS,
        )


# -----------------------------------------------------------------------------
# EOS Test One Interface
# -----------------------------------------------------------------------------


def eos_test_one_interface(
    device: Device, test_case: InterfaceTestCase, iface_oper_status: dict
):
    if_name = test_case.test_case_id()

    # if the interface does not exist on the device, then the test fails, and we
    # go onto the next text.

    if not iface_oper_status:
        yield TestCaseFailed(
            device=device,
            test_case=test_case,
            field=if_name,
            measurement=None,
            error=f"Missing expected interface: {if_name}",
        )
        return

    # transform the CLI data into a measurment instance for consistent
    # comparison with the expected values.

    measurement = EosInterfaceMeasurement.from_cli(iface_oper_status)
    should_oper_status = test_case.expected_results

    if should_oper_status.used != measurement.used:
        yield TestCaseFailed(
            device=device,
            test_case=test_case,
            field="used",
            measurement=measurement.used,
            error=f"Mismatch: used: expected {should_oper_status.used}, measured {measurement.used}",
        )

    # if the interface is not being used, then no more checks are required.

    if not should_oper_status.used:
        return

    # -------------------------------------------------------------------------
    # Interface is USED ... check other attributes
    # -------------------------------------------------------------------------

    failures = 0
    for field in ("oper_up", "desc", "speed"):

        exp_val = getattr(should_oper_status, field)
        msrd_val = getattr(measurement, field)

        if exp_val == msrd_val:
            continue

        failures += 1
        yield TestCaseFailed(
            device=device,
            test_case=test_case,
            measurement=msrd_val,
            field=field,
            error=f"Mismatch: {field}: expected {exp_val}, measured {msrd_val}",
        )

    if not failures:
        yield TestCasePass(device=device, test_case=test_case, measurement=measurement)
