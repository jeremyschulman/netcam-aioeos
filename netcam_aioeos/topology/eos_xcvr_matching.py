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

from typing import Optional
from functools import lru_cache


from netcad.config import netcad_globals


__all__ = ["eos_xcvr_type_matches", "eos_xcvr_model_matches"]


ARISTA_TYPE_ALIAS = {
    "100GBASE-AR4": "100GBASE-LR",
    "10GBASE-AR": "10GBASE-LR",
    "10GBASE-CRA": "10GBASE-CR",
}


@lru_cache()
def get_config_transciver_model(model: str) -> Optional[str]:
    config = netcad_globals.g_config.get("transceivers", {}).get("models")
    return None if not config else config.get(model)


def eos_xcvr_model_matches(expected: str, measured: str) -> bool:

    # do not take the lenth value in consideration.

    if expected.startswith("AOC-S-S-10G"):
        return measured.startswith("AOC-S-S-10G")

    # -AR indicates an Arista vendor optic, so do not use this part in the
    # comparison.

    if measured.endswith("-AR"):
        measured = measured.split("-AR", 1)[0]

    if model_alias := get_config_transciver_model(model=measured):
        measured = model_alias

    return expected == measured


def eos_xcvr_type_matches(expected: str, measured: str) -> bool:

    if type_alias := ARISTA_TYPE_ALIAS.get(measured):
        measured = type_alias

    return expected == measured
