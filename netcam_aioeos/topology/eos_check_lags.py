#  Copyright 2021 Jeremy Schulman
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from collections import defaultdict
from itertools import chain

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

from netcad.topology.checks.check_lags import (
    LagCheckCollection,
    LagCheck,
    LagCheckResult,
    LagCheckExpectedInterfaceStatus,
)

from netcad.device import Device
from netcad.checks import CheckResultsCollection

# -----------------------------------------------------------------------------
# Private Imports
# -----------------------------------------------------------------------------

from netcam_aioeos.eos_dut import EOSDeviceUnderTest


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = ["eos_check_lags", "eos_check_one_lag"]


@EOSDeviceUnderTest.execute_checks.register
async def eos_check_lags(self, testcases: LagCheckCollection) -> CheckResultsCollection:
    """
    This chcek-executor validates that the LAGs on the device match those as
    defined in the design.
    """

    dut: EOSDeviceUnderTest = self
    device = dut.device

    cli_lacp_resp = await dut.eapi.cli("show lacp interface")

    # The EOS data is a dictionary key is port-channel interface name.
    dev_lacp_data = cli_lacp_resp["portChannels"]

    results = list()

    for check in testcases.checks:

        # The test case ID is the port-channel interface name.
        if_name = check.check_id()

        # If the expected LAG does not exist raise that failure and continue
        # with the next interface.

        if not (lag_status := dev_lacp_data.get(if_name)):
            result = LagCheckResult(device=device, check=check, measurement=None)
            results.append(result)
            continue

        eos_check_one_lag(
            device=device, check=check, lag_status=lag_status, results=results
        )

    return results


def eos_check_one_lag(
    device: Device, check: LagCheck, lag_status: dict, results: CheckResultsCollection
):
    """
    Validates the checks for one specific LAG on the device.
    """

    po_interfaces = lag_status["interfaces"]

    # TODO: presenting this code is **ASSUMING** that the given LAG is enabled
    #       in the design.  The test-case does account for this setting; but not
    #       checking it.  Need to implement that logic.

    # TODO: each test-case interface has an `enabled` setting to account for
    #       whether or not the interface is expected to be in the bundled state.
    #       the code below is currently not checking this setting.  Need to
    #       implement that logic.

    result = LagCheckResult(device=device, check=check)
    msrd = result.measurement

    # -------------------------------------------------------------------------
    # check the interface bundle status.  we will use a defaultdict-list to find
    # any non-bundled values.
    # -------------------------------------------------------------------------

    bundle_status = defaultdict(list)
    for if_name, if_data in po_interfaces.items():
        bundle_status[if_data["actorPortStatus"]].append(if_name)

    bundle_status.pop("bundled")

    # if there are any keys remaining in the bundled_status dictionary this
    # means that there are interfaces in a non bundled state.  Need to report
    # this as a failure.

    iface_unbundled_state = {
        if_name: False for if_name in list(chain.from_iterable(bundle_status.values()))
    }

    lag_down = len(iface_unbundled_state) == len(po_interfaces)

    # -------------------------------------------------------------------------
    # Check for any missing or extra interfaces in the port-channel liss.
    # -------------------------------------------------------------------------

    msrd.enabled = not lag_down
    msrd.interfaces = [
        LagCheckExpectedInterfaceStatus(
            enabled=iface_unbundled_state.get(if_name, True), interface=if_name
        )
        for if_name in po_interfaces
    ]

    results.append(result.measure())
