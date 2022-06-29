# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.bgp_peering.checks import (
    BgpRoutersCheckCollection,
    BgpRouterCheck,
    BgpRouterCheckResult,
)

from netcad.checks import check_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest
from .eos_check_bgp_peering_defs import EOS_DEFAULT_VRF_NAME

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


@EOSDeviceUnderTest.execute_checks.register
async def check_bgp_neighbors(
    self, check_bgp_routers: BgpRoutersCheckCollection
) -> trt.CheckResultsCollection:
    """
    This function is responsible for validating the EOS device IP BGP neighbors
    are operationally correct.

    Parameters
    ----------
    self: EOSDeviceUnderTest
        *** DO NOT TYPEHINT because registration will fail if you do ***

    check_bgp_routers: BgpRoutersCheckCollection
        The checks associated for BGP Routers defined on the device

    Returns
    -------
    trt.CheckResultsCollection - The results of the checks
    """
    results: trt.CheckResultsCollection = list()
    checks = check_bgp_routers.checks
    dut: EOSDeviceUnderTest = self

    dev_data = await dut.api_cache_get(key="bgp-summary", command="show ip bgp summary")

    for rtr_chk in checks:
        _check_router_vrf(dut=dut, check=rtr_chk, dev_data=dev_data, results=results)

    return results


# -----------------------------------------------------------------------------
#
#                                 PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def _check_router_vrf(
    dut: EOSDeviceUnderTest,
    check: BgpRouterCheck,
    dev_data: dict,
    results: trt.CheckResultsCollection,
):

    dev_data = dev_data["vrfs"][check.check_params.vrf or EOS_DEFAULT_VRF_NAME]

    result = BgpRouterCheckResult(device=dut.device, check=check)
    msrd = result.measurement

    # from the device, routerId is a string
    msrd.router_id = dev_data.get("routerId", "")

    # from the device, asn is an int
    msrd.asn = dev_data.get("asn", -1)

    results.append(result.measure())
