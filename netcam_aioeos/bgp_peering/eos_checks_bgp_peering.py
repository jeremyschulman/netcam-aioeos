# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from types import MappingProxyType

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.bgp_peering.checks import (
    BgpNeighborsCheckCollection,
    BgpDeviceCheck,
    BgpNeighborCheck,
)

from netcad.bgp_peering.bgp_nei_state import BgpNeighborState


from netcad.checks import check_result_types as trt

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest

DEFAULT_VRF_NAME = "default"

# This mapping table is used to map the EOS Device string value reported in the
# "show" command to the BGP neighbor state Enum defined in the check expected
# value.

EOS_MAP_BGP_STATES: MappingProxyType[str, BgpNeighborState] = MappingProxyType(
    {
        "Idle": BgpNeighborState.IDLE,
        "Connect": BgpNeighborState.CONNECT,
        "Active": BgpNeighborState.ACTIVE,
        "OpenSent": BgpNeighborState.OPEN_SENT,
        "OpenConfirm": BgpNeighborState.OPEN_CONFIRM,
        "Established": BgpNeighborState.ESTABLISHED,
    }
)


class EosBgpPeeringServiceChecker(EOSDeviceUnderTest):
    @EOSDeviceUnderTest.execute_checks.register
    async def check_neeighbors(  # noqa
        self, check_collection: BgpNeighborsCheckCollection
    ) -> trt.CheckResultsCollection:

        results: trt.CheckResultsCollection = list()
        checks = check_collection.checks

        dev_data = await self.eapi.cli("show ip bgp summary")

        # TODO: right now, only vrf=default is supported.
        #       need to enhance the module to support multiple VRFs, but this
        #       is not an immediate need

        _check_device_vrf(
            dut=self, check=checks.device, dev_data=dev_data, results=results
        )

        for nei_check in checks.neighbors:
            _check_bgp_neighbor(
                dut=self, check=nei_check, dev_data=dev_data, results=results
            )

        return results


def _check_device_vrf(
    dut: EOSDeviceUnderTest,
    check: BgpDeviceCheck,
    dev_data: dict,
    results: trt.CheckResultsCollection,
) -> bool:

    dev_data = dev_data["vrfs"][DEFAULT_VRF_NAME]
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


def _check_bgp_neighbor(
    dut: EOSDeviceUnderTest,
    check: BgpNeighborCheck,
    dev_data: dict,
    results: trt.CheckResultsCollection,
) -> bool:
    check_pass = True

    params = check.check_params
    expected = check.expected_results

    rtr_data = dev_data["vrfs"][params.vrf or DEFAULT_VRF_NAME]
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
