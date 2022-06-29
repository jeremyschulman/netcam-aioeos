# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.bgp_peering.checks import (
    BgpNeighborsCheckCollection,
    BgpNeighborCheck,
    BgpNeighborCheckResult,
)

from netcad.checks import check_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest
from .eos_check_bgp_peering_defs import EOS_DEFAULT_VRF_NAME, EOS_MAP_BGP_STATES

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


@EOSDeviceUnderTest.execute_checks.register
async def check_neeighbors(
    self, check_collection: BgpNeighborsCheckCollection
) -> trt.CheckResultsCollection:
    dut: EOSDeviceUnderTest = self

    results: trt.CheckResultsCollection = list()
    checks = check_collection.checks

    dev_data = await dut.api_cache_get(key="bgp-summary", command="show ip bgp summary")

    for nei_check in checks:
        _check_bgp_neighbor(
            dut=dut, check=nei_check, dev_data=dev_data, results=results
        )

    return results


# -----------------------------------------------------------------------------
#
#                                 PRIVATE CODE BEGINS
#
# -----------------------------------------------------------------------------


def _check_bgp_neighbor(
    dut: EOSDeviceUnderTest,
    check: BgpNeighborCheck,
    dev_data: dict,
    results: trt.CheckResultsCollection,
):
    """
    This function checks one BGP neighbor.  A check is considered to pass if and
    only if:

        (1) The neighbor exists
        (2) The neighbor ASN matches expected value
        (3) The BGP state matches expected value

    Notes
    -----
    The `results` argument is appended with check results items.

    Parameters
    ----------
    dut: EOSDeviceUnderTest
        The instance of the DUT

    check: BgpNeighborCheck
        The instance of the specific BGP neighbor check

    dev_data: dict
        The EOS device output data for the show command.

    results: trt.CheckResultsCollection
        The accumulation of check results.
    """

    params = check.check_params
    result = BgpNeighborCheckResult(device=dut.device, check=check)

    rtr_data = dev_data["vrfs"][params.vrf or EOS_DEFAULT_VRF_NAME]
    rtr_neis = rtr_data.get("peers", {})

    # if the neighbor for the expected remote IP does not exist, then record
    # that result, and we are done checking this neighbor.

    if not (nei_data := rtr_neis.get(params.nei_ip)):
        result.measurement = None
        results.append(result.measure())
        return

    # Store the measurements

    msrd = result.measurement
    msrd.remote_asn = nei_data["asn"]
    msrd.state = EOS_MAP_BGP_STATES[nei_data["peerState"]]

    results.append(result.measure())
