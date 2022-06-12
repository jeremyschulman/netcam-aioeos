# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from types import MappingProxyType
from netcad.bgp_peering.bgp_nei_state import BgpNeighborState


EOS_DEFAULT_VRF_NAME = "default"

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
