from typing import List, Dict
from .base import Base
from .asset import Asset


class BorrowerDetailsFromModel(Base):
    debt: float
    collateral_value: float
