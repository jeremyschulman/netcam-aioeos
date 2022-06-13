from ..eos_dut import EOSDeviceUnderTest
from .eos_check_vlans import eos_check_vlans
from .eos_check_switchports import eos_check_switchports

__all__ = ()

EOSDeviceUnderTest.execute_checks.register(eos_check_vlans)
EOSDeviceUnderTest.execute_checks.register(eos_check_switchports)
