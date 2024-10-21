from typing import Any, Dict, List, Optional, Union

from .asset import Asset
from .base import Base


class AssetValueAndRiskFactors(Base):
    # all are human readable
    collateral_factor: float
    liquidation_factor: float
    # in denomination of asset
    exposure: int


class AssetMetadata(Base):
    share: Optional[int] = None  # 1000000 means 100%
    amount: int
    # value: int # denomination of numeraire
    current_amount: (
        int  # only value that changes (decreases) over multiple liquidations
    )
    risk_metadata: AssetValueAndRiskFactors


class AuctionInformation(Base):
    start_debt: int  # Originally uint128
    base: int  # Originally uint64
    cutoff_timestamp: int  # Originally uint32
    start_time: int  # Originally uint32
    start_price_multiplier: int  # Originally uint16
    min_price_multiplier: int  # Originally uint16
    in_auction: bool
    creditor: str  # Address, represented as a string
    assets: Dict[Asset, AssetMetadata]
    minimum_margin: int = 0
    numeraire: Asset


class LendingPoolLiquidationConfig(Base):
    max_initiation_fee: int
    max_termination_fee: int
    initiation_weight: int
    termination_weight: int
    penalty_weight: int


class LiquidationConfig(Base):
    base: int
    maximum_auction_duration: int
    start_price_multiplier: int
    min_price_multiplier: int
    minimum_margin: int = 0
    lending_pool: LendingPoolLiquidationConfig


class AssetsInMarginAccount(Base):
    asset: Asset
    metadata: AssetMetadata


class MarginAccount(Base):
    address: str
    assets: List[AssetsInMarginAccount]
    debt: int
    numeraire: Asset

    # def calculate_liquidation_value(self):
    # return sum([asset.metadata.value * asset.metadata.risk_metadata.liquidation_factor for asset in self.assets])

    # def is_liquidatable(self):
    # return self.calculate_liquidation_value() <= self.debt


class Ranges(Base):
    collateral_factor_range: range | list
    liquidation_factor_range: Optional[range | list] = None
    exposure_range: range | list
