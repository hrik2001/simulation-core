from .base import Base
from .chain import Chain
from .pricing import PricingMetadata
from typing import Optional


class Asset(Base):
    """
    Data model for a generic ERC-20 Asset
    """

    symbol: str
    name: str
    decimals: int = 0
    contract_address: str
    chain: Chain
    pricing_metadata: Optional[PricingMetadata] = None

    def __hash__(self) -> int:
        return f"{self.symbol}-{self.name}-{self.decimals}-{self.contract_address}-{self.chain.chain_id}".__hash__()

    def __str__(self) -> str:
        return f"<Asset: {self.name}>"

    def __repr__(self) -> str:
        return f"<Asset: {self.name}>"


class ConcentratedLiquidityAssetPosition(Base):
    usd_value_invested: float
    interval_spread: float
    liquidity_estimate: Optional[float] = None
    lower_price: Optional[float] = None
    upper_price: Optional[float] = None


class ConcentratedLiquidityAsset(Asset):
    token0: Asset
    token1: Asset
    fee: int
    position: ConcentratedLiquidityAssetPosition

class SimCoreUniswapLPPosition(Asset):
    token0: Asset
    token1: Asset
    # large numbers hence it's charfield
    tickLower: str
    tickUpper: str
    liquidity: str
    token_id: str


    def __str__(self):
        return f"{self.token0}-{self.token1}-{self.token_id}"