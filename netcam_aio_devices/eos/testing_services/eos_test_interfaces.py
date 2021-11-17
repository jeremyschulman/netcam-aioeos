from operator import itemgetter

from pydantic import dataclasses, PositiveInt, root_validator

from netcad.testing_services import TestCasePass, TestCaseFailed
from netcam_aio_devices.eos import Device
from netcad.testing_services.interfaces import InterfaceTestCases, InterfaceTestCase

__all__ = ["eos_testcases_interfaces", "eos_test_one_interface"]


BITS_TO_MBS = 10 ** -6


@dataclasses.dataclass()
class EosInterfaceMeasurement:
    """
    This dataclass is used to store the values as retrieved from the EOS device
    into a set of attributes that align to the test-case.
    """

    used: bool
    oper_up: bool
    desc: str
    speed: PositiveInt

    # these are the CLI keys that will be mapped to the above fields.
    map_fields = itemgetter(
        "linkStatus", "lineProtocolStatus", "description", "bandwidth"
    )

    @classmethod
    def from_cli(cls, payload: dict):
        """return an instance of the measurement after mapping the CLI fields"""
        return cls(*cls.map_fields(payload))

    @root_validator(pre=True)
    def map_data(cls, values):  # noqa
        return dict(
            used=values["used"] != "disabled",
            oper_up=values["oper_up"] == "up",
            desc=values["desc"],
            speed=values["speed"] * BITS_TO_MBS,
        )


def eos_test_one_interface(
    device: Device, test_case: InterfaceTestCase, iface_oper_status: dict
):
    if_name = test_case.test_case_id()

    # if the interface does not exist on the device, then the test fails,
    # and we go onto the next text.

    if not iface_oper_status:
        yield TestCaseFailed(
            device=device,
            test_case=test_case,
            measurement=None,
            error=f"Missing expected interface: {if_name}",
        )
        return

    # transform the CLI data into a measurment instance for consistent
    # comparison with the expected values.

    measurement = EosInterfaceMeasurement.from_cli(iface_oper_status)

    should_oper_status = test_case.expected_results

    yield TestCasePass(device=device, test_case=test_case, measurement=measurement)


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
