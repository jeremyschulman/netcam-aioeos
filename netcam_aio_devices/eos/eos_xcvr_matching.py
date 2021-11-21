__all__ = ["eos_xcvr_type_matches", "eos_xcvr_model_matches"]


ARISTA_TYPE_ALIAS = {
    "100GBASE-AR4": "100GBASE-LR",
    "10GBASE-AR": "10GBASE-LR",
    "10GBASE-CRA": "10GBASE-CR",
}


def eos_xcvr_model_matches(expected: str, measured: str) -> bool:

    # do not take the lenth value in consideration.

    if expected.startswith("AOC-S-S-10G"):
        return measured.startswith("AOC-S-S-10G")

    # -AR indicates an Arista vendor optic, so do not use this part in the
    # comparison.

    if measured.endswith("-AR"):
        measured = measured.split("-AR", 1)[0]

    return expected == measured


def eos_xcvr_type_matches(expected: str, measured: str) -> bool:

    if type_alias := ARISTA_TYPE_ALIAS.get(measured):
        measured = type_alias

    return expected == measured
