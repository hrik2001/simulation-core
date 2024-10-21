from typing import Dict, List

from .asset import Asset
from .base import Base


class BorrowerDetailsFromModel(Base):
    debt: float
    collateral_value: float
