from .base import Base
from .chain import Chain
from .asset import Asset
from .pricing import PricingMetadata
from typing import Optional, List, Dict, Any, Union
from ..entities.chain import ethereum
from ..exceptions import PriceNotPopulated
from ..logging import configure_multiprocess_logging, get_logger
import requests
from web3 import Web3
from collections import defaultdict

from ..caching import cache


class SimulationTime(Base):
    timestamp: int
    chain: Chain
    # TODO: switch to pandas later
    # Issues: problem with validation of dataframe
    # Implementation: use dataframe with timestamp as index
    prices: Dict[Asset, Dict[int, float]]
    gas_prices: Dict[int, float] = defaultdict(int)
    logging_queue: Optional[Any] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.logging_queue is not None:
            configure_multiprocess_logging(self.logging_queue)
        self.logger = get_logger(__name__)

    def update_by_timestamp(self, new_timestamp: int):
        self.timestamp = new_timestamp

    def get_price(self, asset: Asset) -> float:
        try:
            return self.prices[asset][self.timestamp]
        except KeyError:
            raise PriceNotPopulated(self.timestamp)

    def get_gas(self):
        try:
            return self.gas_prices[self.timestamp]
        except KeyError:
            raise PriceNotPopulated
