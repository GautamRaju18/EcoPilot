"""Auto emission calculation (Business Rule 2)."""
from sqlalchemy.orm import Session

from ..config import settings
from ..models import EmissionFactor


def calculate_co2e(db: Session, *, emission_factor_id: int | None, quantity: float,
                   provided_co2e: float | None) -> float:
    """Return CO2e. If auto-calc is on and a factor is linked, compute
    quantity * factor.co2e_per_unit; otherwise use the provided value."""
    if settings.AUTO_EMISSION_CALC and emission_factor_id:
        factor = db.query(EmissionFactor).get(emission_factor_id)
        if factor:
            return round(quantity * factor.co2e_per_unit, 3)
    return round(provided_co2e or 0.0, 3)
