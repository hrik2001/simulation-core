from ..models.arcadia import (
    AuctionInformation,
    MarginAccount,
    LiquidationConfig,
)
from ..models.asset import Asset
from ..models.time import SimulationTime
from ..models.metrics import SimulationMetrics
from .utils.liquidator import (
    calculate_bid_price,
    calculate_asked_share,
    update_portfolio_balance,
    dry_run_update_portfolio_balance,
    is_liquidatable,
    is_account_fully_liquidated,
    prepare_assets_in_margin_account,
)
from typing import Dict, List, Optional, Any, DefaultDict
from ..exceptions import (
    AuctionDoesNotExist,
    NotEnoughLiquidity,
    AuctionDoesExist,
    AccountNotLiquidatable,
)
from ..logging import configure_multiprocess_logging, get_logger
from ..models.base import Base
from collections import defaultdict


class LiquidationEngine(Base):
    liquidation_config: LiquidationConfig
    simulation_time: SimulationTime
    auction_information: Dict[str, AuctionInformation] = {}
    # `auctions_to_end`: Accounts marked for removal from auction
    auctions_to_end: List[str] = []
    # `all_liquidated_accounts`: Contains fully liquidated accounts. Accounts with no collateral
    all_liquidated_accounts: List[str] = []
    logging_queue: Optional[Any] = None
    accounts: List[MarginAccount] = []
    protocol_revenue: int = 0
    protocol_revenue_per_asset: Any = defaultdict(int)

    # @model_serializer
    # def ser_model(self) -> Dict[str, Any]:
    #     # result_context = {}
    #     # result_context["simulation_time"] = self.simulation_time.timestamp
    #     # result_context["all_liquidated_accounts"] = self.all_liquidated_accounts

    #     auctions = {}
    #     for key, value in self.auction_information.items():
    #         auctions[key] = {
    #             "start_debt": value.start_debt/(10**value.numeraire.decimals),
    #             "assets": {k.symbol: v.current_amount/(10**k.decimals) for k, v in value.assets.items()},
    #             "nummeraire": value.numeraire.symbol
    #         }
    #     # result_context["auctions"] = auctions
    #     return auctions

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.logging_queue is not None:
            configure_multiprocess_logging(self.logging_queue)
        self.logger = get_logger(__name__)

    def add_auction_information(self, account: str, auction_info: AuctionInformation):
        """
        Add auction information
        This method should be used to start an auction
        """
        self.auction_information[account] = auction_info

    def get_auction_information(self, account: str):
        """
        Get auction information, raises no exception if auction doesn't exist
        Assumes that all data is filled
        """
        return self.auction_information.get(account, None)

    def liquidate(self, account: MarginAccount):
        """
        Liquidate the account
        """

        # Get auction information
        if self.get_auction_information(account.address) is not None:
            raise AuctionDoesExist

        # Calculate liquidation
        # if not account.is_liquidatable():
        if not is_liquidatable(
            account, self.simulation_time, account.numeraire.decimals
        ):
            raise AccountNotLiquidatable

        now = self.simulation_time.timestamp
        cutoff_timestamp = now + self.liquidation_config.maximum_auction_duration

        auction_information = AuctionInformation(
            start_debt=account.debt,
            base=self.liquidation_config.base,
            cutoff_timestamp=cutoff_timestamp,
            start_time=now,
            start_price_multiplier=self.liquidation_config.start_price_multiplier,
            min_price_multiplier=self.liquidation_config.min_price_multiplier,
            in_auction=True,
            creditor=account.address,
            numeraire=account.numeraire,
            minimum_margin=self.liquidation_config.minimum_margin,
            # TODO: share calc
            assets=prepare_assets_in_margin_account(
                account.assets, self.simulation_time
            ),
            # assets={
            # asset.asset: asset.metadata
            # for asset in account.assets
            # }
        )

        self.add_auction_information(account.address, auction_information)

    def bid(self, account: str, asked_amounts: Dict[Asset, int]):
        """
        Bid (and get) a combination of assets

        returns Boolean to represent success/failure
        raises AuctionDoesNotExist if the auction doesn't exist
        """
        try:
            self.auction_information[account]
        except KeyError:
            raise AuctionDoesNotExist

        asked_share = calculate_asked_share(
            self.auction_information[account], asked_amounts
        )

        bid_price = calculate_bid_price(
            self.auction_information[account],
            asked_share,
            self.simulation_time.timestamp,
        )

        try:
            update_portfolio_balance(self.auction_information[account], asked_amounts)

            margin_account = None
            for i in self.accounts:
                if i.address == account:
                    margin_account = i
            if margin_account is None:
                raise Exception("Account not found")

            if margin_account.debt <= bid_price:
                self.protocol_revenue += int(bid_price - margin_account.debt)
                margin_account.debt = 0

                numeraire = self.auction_information[account].numeraire
                prices_per_asset = {}
                total_bid_cost = 0
                for bid_asset, bid_amount in asked_amounts.items():
                    prices_per_asset[bid_asset.symbol] = (
                        (bid_amount / (10**bid_asset.decimals))
                        * self.simulation_time.get_price(bid_asset)
                        * (10**numeraire.decimals)
                    )
                    total_bid_cost += (
                        (bid_amount / (10**bid_asset.decimals))
                        * self.simulation_time.get_price(bid_asset)
                        * (10**numeraire.decimals)
                    )
                for symbol, asset_revenue in prices_per_asset.items():
                    self.protocol_revenue_per_asset[symbol] += (
                        (asset_revenue / total_bid_cost)
                        * (bid_price - margin_account.debt)
                    ) / (10**numeraire.decimals)
            else:
                margin_account.debt -= int(bid_price)

            numeraire = self.auction_information[account].numeraire
            cutoff_timestamp = self.auction_information[account].cutoff_timestamp
            minimum_margin = self.auction_information[account].minimum_margin
            used_margin = margin_account.debt + minimum_margin
            collateral_value = 0
            for asset, metadata in self.auction_information[account].assets.items():
                collateral_value += (
                    self.simulation_time.get_price(asset)
                    * metadata.current_amount
                    * (10 ** (numeraire.decimals - asset.decimals))
                )

            if (collateral_value >= used_margin) or (used_margin == minimum_margin):
                # happy flow
                self.auctions_to_end.append(account)
                if is_account_fully_liquidated(self.auction_information[account]):
                    self.all_liquidated_accounts.append(account)
            elif is_account_fully_liquidated(self.auction_information[account]):
                # unhappy flow
                self.auctions_to_end.append(account)
                self.all_liquidated_accounts.append(account)
            elif self.simulation_time.timestamp > cutoff_timestamp:
                # unhappy flow
                # not added to `all_liquidated_accounts` since account can be put to auction again
                self.auctions_to_end.append(account)

            return True, bid_price
        except NotEnoughLiquidity:
            return False, bid_price

    def dry_run_bid(self, account: str, asked_amounts: Dict[Asset, int]):
        """
        Do a dry run for bid to:
            - Check if there are enough reserves (can be checked by fetching AuctionInformation too)
            - Get a quote of the bid price

        returns Boolean to represent success/failure
        raises AuctionDoesNotExist if the auction doesn't exist
        """
        try:
            self.auction_information[account]
        except KeyError:
            raise AuctionDoesNotExist

        asked_share = calculate_asked_share(
            self.auction_information[account], asked_amounts
        )

        bid_price = calculate_bid_price(
            self.auction_information[account],
            asked_share,
            self.simulation_time.timestamp,
        )

        try:
            dry_run_update_portfolio_balance(
                self.auction_information[account], asked_amounts
            )
            return (True, bid_price)
        except NotEnoughLiquidity:
            return (False, bid_price)

    def safe_knockoff(self):
        """
        Safely removes accounts that have been marked for ending the auction
        Should be called after the liquidator has called `scan_auctions`
        """
        for account in self.auctions_to_end:
            # self.logger.debug(f"Removing {account} from active auctions")
            del self.auction_information[account]

        self.auctions_to_end = []

    def get_metrics(self):
        # Make sure we do a safe knockoff just so that we
        # get latest data
        self.safe_knockoff()

        insolvent_values_per_account = defaultdict(int)
        insolvent_values_per_asset = defaultdict(int)

        for account, auction_information in self.auction_information.items():
            for asset, asset_metadata in auction_information.assets.items():
                current_amount_in_numeraire = (
                    (asset_metadata.current_amount / (10**asset.decimals))
                    * self.simulation_time.get_price(asset)
                    * (10**auction_information.numeraire.decimals)
                )
                insolvent_values_per_account[account] += current_amount_in_numeraire
                insolvent_values_per_asset[asset] += current_amount_in_numeraire

        # # self.logger.debug(self.model_dump_json(exclude={"logging_queue", "logger"}))
        return SimulationMetrics(
            insolvent_accounts=len(self.auction_information),
            insolvent_values_per_account=insolvent_values_per_account,
            insolvent_values_per_asset=insolvent_values_per_asset,
        )
