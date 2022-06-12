# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.bgp_peering.checks import (
    BgpRoutersCheckCollection,
    BgpRouterCheck,
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


class EosBgpRouterChecker(EOSDeviceUnderTest):
    @EOSDeviceUnderTest.execute_checks.register
    async def check_neeighbors(
        self, check_collection: BgpRoutersCheckCollection
    ) -> trt.CheckResultsCollection:

        results: trt.CheckResultsCollection = list()
        checks = check_collection.checks

        dev_data = await self.api_cache_get(
            key="bgp-summary", command="show ip bgp summary"
        )

        for rtr_chk in checks:
            _check_router_vrf(
                dut=self, check=rtr_chk, dev_data=dev_data, results=results
            )

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
) -> bool:

    dev_data = dev_data["vrfs"][check.check_params.vrf or EOS_DEFAULT_VRF_NAME]

    expected = check.expected_results
    check_pass = True

    # from the device, routerId is a string
    if (rtr_id := dev_data.get("routerId", "")) != expected.router_id:
        results.append(
            trt.CheckFailFieldMismatch(
                check=check, device=dut.device, field="router_id", measurement=rtr_id
            )
        )
        check_pass = False

    # from the device, asn is an int

    if (dev_asn := dev_data.get("asn", -1)) != expected.asn:
        results.append(
            trt.CheckFailFieldMismatch(
                check=check, device=dut.device, field="asn", measurement=dev_asn
            )
        )
        check_pass = False

    if check_pass:
        results.append(
            trt.CheckPassResult(
                device=dut.device,
                check=check,
                measurement=dict(routerId=rtr_id, asn=dev_asn),
            )
        )

    return check_pass
