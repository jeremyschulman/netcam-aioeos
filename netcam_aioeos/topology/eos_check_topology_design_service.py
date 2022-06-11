from netcad.topology import TopologyDesignService

from ..netcam_design_service import DesignServiceChecker
from ..eos_dut import EOSDeviceUnderTest


@EOSDeviceUnderTest.service_checker.register(TopologyDesignService)
class EosTopologyServiceChecker(DesignServiceChecker[TopologyDesignService]):
    def __init__(self, dut, name: str):
        super().__init__(dut, name=name)

        from .eos_check_device_info import eos_check_device_info

        dut.execute_checks.register(eos_check_device_info)

        from .eos_check_cabling import eos_test_cabling

        dut.execute_checks.register(eos_test_cabling)

        from .eos_check_ipaddrs import eos_test_ipaddrs

        dut.execute_checks.register(eos_test_ipaddrs)

        from .eos_check_interfaces import eos_check_interfaces

        dut.execute_checks.register(eos_check_interfaces)

        from .eos_check_transceivers import eos_check_transceivers

        dut.execute_checks.register(eos_check_transceivers)
