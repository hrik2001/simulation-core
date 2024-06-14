from .liquidation_engine import LiquidationEngine
from ..models.time import SimulationTime
from ..models.arcadia import AuctionInformation, MarginAccount
from ..slippage.slippage import SlippageCalculator
from ..exceptions import AuctionDoesExist
from ..logging import configure_multiprocess_logging, get_logger
from .utils.liquidator import is_liquidatable
from typing import Dict, List, Optional, Any
import numpy as np
from pydantic import model_serializer

# from uuid import UUID, uuid4


slippage_config = SlippageCalculator()


class Liquidator:
    """
    Liquidator agent
    """

    def __init__(
        self,
        liquidation_engine: LiquidationEngine,
        # A very general case, ignored for now
        # balances: Dict[Asset, int],
        balance: int,  # in terms of Numeraire
        sim_time: SimulationTime,
        # address: Optional[str] = None,
        liquidator_address: Optional[str] = None,
        logging_queue: Optional[Any] = None,
    ):
        """
        Initializes with liquidation engine instance, balances, simulation time instance
        One of the asset has to be Numeraire
        """
        self.liquidation_engine = liquidation_engine
        # self.balances = balances
        self.balance = balance
        self.sim_time = sim_time
        self.logging_queue = logging_queue
        # self.address = address
        self.liquidator_address = liquidator_address
        if self.logging_queue is not None:
            configure_multiprocess_logging(self.logging_queue)
        self.logger = get_logger(__name__)

    def scan_account(self, account: MarginAccount) -> bool:
        """
        Scans margin account to check if an account can be liquidated or not
        """
        if (
            is_liquidatable(account, self.sim_time, account.numeraire.decimals)
            and account.address not in self.liquidation_engine.all_liquidated_accounts
        ):
            # self.logger.debug(f"[SCAN] Account {account.address} is liquidatable")
            try:
                self.liquidation_engine.liquidate(account)
                # self.logger.debug(f"[SCAN] {account.address} has been put for auction")
            except AuctionDoesExist:
                self.logger.debug(f"[SCAN] {account.address} is already on auction")
                return False
            return True
        return False

    @model_serializer
    def model_ser(
        self,
        auction_information: AuctionInformation,
        current_amount_numeraire: int,
        trading_fee: int,
        slippage: int,
        gas: int,
        bid_price: int,
    ):
        result_context = {}
        result_context["bid_revenue"] = current_amount_numeraire / (
            10**auction_information.numeraire.decimals
        )
        result_context["trading_fees"] = (
            trading_fee  # /(10**auction_information.numeraire.decimals)
        )
        result_context["slippage"] = slippage / (
            10**auction_information.numeraire.decimals
        )
        result_context["gas"] = gas / (10**auction_information.numeraire.decimals)
        result_context["bid_price"] = bid_price / (
            10**auction_information.numeraire.decimals
        )
        result_context["profit"] = (
            current_amount_numeraire - slippage - bid_price - gas - trading_fee
        ) / (10**auction_information.numeraire.decimals)

        return result_context

    def scan_auctions(self):
        """
        Scans and bids for viable bids at an ongoing auction
        """
        bid_log = {}
        gas_ohlc_price_high = self.sim_time.get_gas()

        for (
            account,
            auction_information,
        ) in self.liquidation_engine.auction_information.items():
            bid_param = {}
            bid_param_log = {}
            bid_flag = False
            total_profit = 0

            # Gas works in the following manner
            # 20_000 + 60_000 + len(auctionAssets)*(100_000)  + len(auctionAssets)*(3000) = initialization
            # => 80_000 + 103_000*len(auctionAssets)
            # 15_000 + 100_000 + (20_000*len(bids)) + (90_000*len(bids) + 6000) = bidding
            # => 115_000 + 110_000*len(bids)
            # (90_000*(len(auctionAssets) - len(bids))+ 60_000) + 20_000 + 200_000 termination
            # => 280_000 + 90_000*(len(auctionAssets)) - 90_000*(len(bids))
            # Let us assume gas = A(len(bids)) + B(len(auctionAssets)) + C where A, B, C are constants
            # => 475_000 + 193_000*len(auctionAssets) + 20_000*len(bids)

            if auction_information.start_time == self.sim_time:
                gas_initialization = (
                    80_000 + (103_000 * len(auction_information.assets))
                ) * gas_ohlc_price_high
            else:
                gas_initialization = 0

            gas_bidding = 115_000 * gas_ohlc_price_high
            gas_bidding_constant = gas_bidding

            for asset, asset_metadata in auction_information.assets.items():
                current_amount = asset_metadata.current_amount
                current_amount_numeraire = (
                    (current_amount / (10**asset.decimals))
                    * self.sim_time.get_price(asset)
                    * (10**auction_information.numeraire.decimals)
                )

                status, bid_price = self.liquidation_engine.dry_run_bid(
                    account, {asset: current_amount}
                )
                slippage = slippage_config.get_slippage(
                    asset.contract_address,
                    auction_information.numeraire.contract_address,
                    current_amount / (10**asset.decimals),
                )
                slippage = (
                    slippage
                    * self.sim_time.get_price(asset)
                    * (10**auction_information.numeraire.decimals)
                )
                # asset_amount = current_amount/(10 ** asset.decimals) * self.sim_time.get_price(asset)

                # #TODO: renable slippage
                # slippage = 0

                # self.logger.debug(
                # f"{account=} {asset=} price={current_amount_numeraire/(10**auction_information.numeraire.decimals)} bid_price={bid_price/(10**auction_information.numeraire.decimals)}"
                # )

                # TODO: integrate gas here
                gas = 110_000 * gas_ohlc_price_high

                trading_fee = 0
                profit = (
                    current_amount_numeraire - slippage - gas - trading_fee > bid_price
                )

                if status:
                    if profit:
                        bid_param[asset] = current_amount
                        total_profit += (
                            current_amount_numeraire
                            - slippage
                            - bid_price
                            - gas
                            - trading_fee
                        )
                        gas_bidding += gas
                        bid_flag = True
                    else:
                        bid_param[asset] = 0

                # logging
                bid_param_log[asset.symbol] = self.model_ser(
                    auction_information,
                    current_amount_numeraire,
                    trading_fee,
                    slippage,
                    gas,
                    bid_price,
                )

            bid_log[auction_information.creditor] = {
                "bids": bid_param_log,
                "total_profit": 0,
            }

            # Termination condition
            if (
                sum(
                    [
                        v.current_amount - bid_param.get(k, 0)
                        for k, v in auction_information.assets.items()
                    ]
                )
                == 0
            ):
                gas_termination = (
                    280_000
                    + 90_000 * (len(auction_information.assets))
                    - 90_000 * (len(bid_param)) * gas_ohlc_price_high
                )
            else:
                gas_termination = 0

            total_gas_without_bids = (
                gas_bidding_constant + gas_termination + gas_initialization
            )

            if bid_flag:
                # INFO: calculation of gas
                if total_profit - total_gas_without_bids > 0:
                    # print((total_profit - total_gas_without_bids )/10**auction_information.numeraire.decimals, "<profit")
                    bid_log[auction_information.creditor]["total_profit"] = (
                        total_profit - total_gas_without_bids
                    ) / 10**auction_information.numeraire.decimals
                    _, bid_price = self.liquidation_engine.bid(account, bid_param)
                    if _:
                        # self.logger.debug(
                        # f"[BID] {bid_param} {total_profit=} {total_profit-gas=} {bid_price=}"
                        # )
                        pass
                    else:
                        # self.logger.error(f"[BID ERROR] {bid_param=} {bid_price=}")
                        pass
                else:
                    # self.logger.error(
                    # f"[BID ERROR]: BID NOT MADE DUE TO GAS {bid_param=} {bid_price=} {total_profit=} {total_gas_without_bids=}"
                    # )
                    pass
            else:
                continue
                # self.logger.debug("No bids made by the liquidator")

        self.liquidation_engine.safe_knockoff()

        return bid_log
