"""Unit scaling between the domain's floats and the solver's integers.

clingo reasons over integers only. Rather than scatter conversions through the fact
renderer and the table generator — where a mismatch would silently shift a determination
by a factor of ten — every conversion lives here and both sides import it.

Scaling is chosen so that no regulatory value loses precision:

* lengths in **centimetres** (a 1 m dimension band is 100, 500 ft is 15240)
* speeds in **centimetres per second** (25 m/s is 2500)
* mass in **grams** (the 250 g small-UA provision is exact)
* population density in **whole people per km²**, rounded **up**, because rounding a
  density down could drop an operation into a lower iGRC row
"""

from __future__ import annotations

import math

CM_PER_M = 100
CMS_PER_MS = 100
G_PER_KG = 1000
M_PER_FT = 0.3048


def m_to_cm(metres: float) -> int:
    """Round up: a 1.001 m aircraft must not be read as fitting the 1 m column."""
    return math.ceil(metres * CM_PER_M - 1e-9)


def ms_to_cms(metres_per_second: float) -> int:
    return math.ceil(metres_per_second * CMS_PER_MS - 1e-9)


def kg_to_g(kilograms: float) -> int:
    return math.ceil(kilograms * G_PER_KG - 1e-9)


def ft_to_cm(feet: float) -> int:
    return round(feet * M_PER_FT * CM_PER_M)


def density_to_int(per_km2: float) -> int:
    """Round up, so a density is never understated into a lower iGRC row."""
    return math.ceil(per_km2 - 1e-9)


def cm_to_m(cm: int) -> float:
    return cm / CM_PER_M


def cms_to_ms(cms: int) -> float:
    return cms / CMS_PER_MS
