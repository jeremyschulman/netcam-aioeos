# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.bgp_peering import checks as bgp_checks
from netcad.checks import check_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest


class EosBgpPeeringServiceChecker(EOSDeviceUnderTest):
    @EOSDeviceUnderTest.execute_checks.register
    async def check_neeighbors(  # noqa
        self, checks: bgp_checks.BgpNeighborsCheckCollection
    ) -> trt.CheckResultsCollection:
        return []
