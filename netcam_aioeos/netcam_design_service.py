from typing import Generic, TypeVar, TYPE_CHECKING, Hashable

from netcad.design import DesignService

if TYPE_CHECKING:
    from .eos_dut import EOSDeviceUnderTest

DS = TypeVar("DS", bound=DesignService)


class DesignServiceChecker(Generic[DS]):
    def __init__(self, dut: "EOSDeviceUnderTest", name: Hashable):
        self.dut = dut
        self.name = name
