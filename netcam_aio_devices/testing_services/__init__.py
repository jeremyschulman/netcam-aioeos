from functools import singledispatch


from netcad.testing_services import (
    device,
    interfaces,
    lags,
    vlans,
    transceivers,
    cabling,
)


__all__ = ["SUPPORTED_TESTING_SERVICES", "executor_test_interfaces"]


@singledispatch
def executor_test_interfaces():
    raise RuntimeError("Missing required os_name handler")


SUPPORTED_TESTING_SERVICES = {
    interfaces.InterfaceTestCases.get_service_name(): executor_test_interfaces
}
