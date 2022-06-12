from ..eos_dut import EOSDeviceUnderTest

from .eos_check_device_info import eos_check_device_info
from .eos_check_cabling import eos_test_cabling
from .eos_check_ipaddrs import eos_test_ipaddrs
from .eos_check_interfaces import eos_check_interfaces
from .eos_check_transceivers import eos_check_transceivers


class EosTopologyServiceChecker(EOSDeviceUnderTest):
    EOSDeviceUnderTest.execute_checks.register(eos_check_device_info)
    EOSDeviceUnderTest.execute_checks.register(eos_test_cabling)
    EOSDeviceUnderTest.execute_checks.register(eos_test_ipaddrs)
    EOSDeviceUnderTest.execute_checks.register(eos_check_interfaces)
    EOSDeviceUnderTest.execute_checks.register(eos_check_transceivers)
