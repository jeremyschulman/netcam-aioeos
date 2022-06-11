from typing import Hashable

from netcad.bgp_peering import BgpPeeringDesignService, checks as bgp_checks
from netcad.checks import check_result_types as trt

from ..netcam_design_service import DesignServiceChecker

from netcam_aioeos.eos_dut import EOSDeviceUnderTest


@EOSDeviceUnderTest.service_checker.register(BgpPeeringDesignService)
class EosBgpPeeringServiceChecker(DesignServiceChecker[BgpPeeringDesignService]):
    def __init__(self, dut, name: Hashable):
        super().__init__(dut, name=name)
        dut.execute_checks.register(self.check_neeighbors)

    async def check_neeighbors(  # noqa
        self, checks: bgp_checks.BgpNeighborsCheckCollection
    ) -> trt.CheckResultsCollection:
        return []
