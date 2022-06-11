from typing import get_args, Type

from netcad.design import DesignService

from .netcam_design_service import DesignServiceChecker


from .vlans.eos_checks_vlan_design_service import EosVlanDesignServiceChecker
from .topology.eos_check_topology_design_service import EosTopologyServiceChecker
from .bgp_peering import EosBgpPeeringServiceChecker


def get_bound_design_service_cls(checker_cls: Type[DesignServiceChecker]):
    return get_args(checker_cls.__orig_bases__[0])[0]


supports: dict[Type[DesignService], Type[DesignServiceChecker]] = {
    get_bound_design_service_cls(cls): cls
    for cls in (
        EosTopologyServiceChecker,
        EosVlanDesignServiceChecker,
        EosBgpPeeringServiceChecker,
    )
}
