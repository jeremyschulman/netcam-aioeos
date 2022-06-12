# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.bgp_peering.checks import (
    BgpNeighborsCheckCollection,
    BgpNeighborCheck,
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


class EosBgpPeeringServiceChecker(EOSDeviceUnderTest):
    @EOSDeviceUnderTest.execute_checks.register
    async def check_neeighbors(
        self, check_collection: BgpNeighborsCheckCollection
    ) -> trt.CheckResultsCollection:

        results: trt.CheckResultsCollection = list()
        checks = check_collection.checks

        dev_data = await self.api_cache_get(
            key="bgp-summary", command="show ip bgp summary"
        )

        for nei_check in checks:
            _check_bgp_neighbor(
                dut=self, check=nei_check, dev_data=dev_data, results=results
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
) -> bool:
    check_pass = True

    params = check.check_params
    expected = check.expected_results

    rtr_data = dev_data["vrfs"][params.vrf or EOS_DEFAULT_VRF_NAME]
    rtr_neis = rtr_data.get("peers", {})

    # if the neighbor for the expected remote IP does not exist, then record
    # that result, and we are done checking this neighbor.

    if not (nei_data := rtr_neis.get(params.nei_ip)):
        results.append(trt.CheckFailNoExists(device=dut.device, check=check))
        return False

    # next check for peer ASN matching.

    if (remote_asn := nei_data["asn"]) != expected.remote_asn:
        check_pass = False
        results.append(
            trt.CheckFailFieldMismatch(
                device=dut.device, check=check, field="asn", measurement=remote_asn
            )
        )

    # check for matching expected BGP state
    peer_state = EOS_MAP_BGP_STATES[nei_data["peerState"]]

    if peer_state != expected.state:
        check_pass = False
        results.append(
            trt.CheckFailFieldMismatch(
                device=dut.device, check=check, field="state", measurement=peer_state
            )
        )

    if check_pass:
        results.append(
            trt.CheckPassResult(
                device=dut.device,
                check=check,
                measurement=nei_data,
            )
        )

    return check_pass
