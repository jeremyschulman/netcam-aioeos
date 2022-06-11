from typing import Hashable

from netcad.vlans import DeviceVlanDesignService
from ..netcam_design_service import DesignServiceChecker


class EosVlanDesignServiceChecker(DesignServiceChecker[DeviceVlanDesignService]):
    def __init__(self, dut, name: Hashable):
        super().__init__(dut, name=name)

        dispatcher = dut.__class__.__dict__["execute_checks"].dispatcher

        from .eos_check_vlans import eos_check_vlans

        dispatcher.register(eos_check_vlans)

        from .eos_check_switchports import eos_check_switchports

        dispatcher.register(eos_check_switchports)
