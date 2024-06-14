"""
A pipeline is one simulation instance
"""

from ..models.asset import Asset
from ..models.chain import Chain
from ..models.base import Base

from ..models.time import SimulationTime
from ..arcadia.liquidation_engine import LiquidationEngine
from ..arcadia.liquidator import Liquidator
from ..models.arcadia import MarginAccount
from ..logging import configure_multiprocess_logging, get_logger
from ..utils import get_mongodb_db
from typing import List, Optional, Any
from collections import defaultdict
import uuid
import numpy as np
import os


class Pipeline(Base):
    # start_timestamp: int
    # end_timestamp: int
    simulation_time: SimulationTime
    liquidation_engine: LiquidationEngine
    liquidators: List[Liquidator]
    accounts: List[MarginAccount]
    numeraire: Asset
    logging_queue: Optional[Any] = None
    pipeline_id: Optional[uuid.UUID] = None
    orchestrator_id: Optional[uuid.UUID] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.logging_queue is not None:
            configure_multiprocess_logging(self.logging_queue)
            self.simulation_time.logging_queue = self.logging_queue
            self.liquidation_engine.logging_queue = self.logging_queue
            for liquidator in self.liquidators:
                liquidator.logging_queue = self.logging_queue

        self.liquidation_engine.accounts = self.accounts
        self.logger = get_logger(__name__)
        # log_directory = "pipeline_logs"
        # log_file = f"{str(self.pipeline_id)}.log"
        # os.makedirs(log_directory, exist_ok=True)
        # if self.orchestrator_id is not None:
        #     os.makedirs(
        #         os.path.join(log_directory, str(self.orchestrator_id)), exist_ok=True
        #     )
        #     log_directory = os.path.join(log_directory, str(self.orchestrator_id))
        # self.log_fd = open(os.path.join(log_directory, log_file), "w")

    def sim_params(self):

        sim_params = {}
        for account in self.accounts:
            for asset in account.assets:
                asset_risk_data = dict(asset.metadata.risk_metadata)
                asset_risk_data["exposure"] = int(asset_risk_data["exposure"]) / (
                    10**asset.asset.decimals
                )
                asset_risk_data["numeraire"] = account.numeraire.symbol
                sim_params.setdefault("asset", {})[asset.asset.symbol] = asset_risk_data

        # sim_params["start_timestamp"] = self.start_timestamp
        # sim_params["end_timestamp"] = self.end_timestamp
        # sim_params["number_of_accounts"] = len(self.accounts)
        # sim_params["number_of_liquidators"] = len(self.liquidators)

        return sim_params

    def sim_accounts(self):
        context = {}

        context["simulation_time"] = self.simulation_time.timestamp

        context["prices"] = self.sim_price()

        accounts = {}

        for account in self.accounts:
            account_normalised = {}

            assets = {}
            for asset in account.assets:

                asset_dict = {}

                asset_dict["share"] = asset.metadata.share
                asset_dict["amount"] = asset.metadata.amount / (
                    10**asset.asset.decimals
                )
                asset_dict["current_amount"] = asset.metadata.current_amount / (
                    10**asset.asset.decimals
                )

                asset_risk_data = dict(asset.metadata.risk_metadata)
                asset_risk_data["exposure"] = int(asset_risk_data["exposure"]) / (
                    10**asset.asset.decimals
                )
                asset_dict["risk_metadata"] = asset_risk_data

                assets[asset.asset.symbol] = asset_dict

            account_normalised["asset_in_margin_account"] = assets

            # numeraire
            account_normalised["debt"] = account.debt / (10**account.numeraire.decimals)
            account_normalised["numeraire"] = account.numeraire.symbol

            accounts[account.address] = account_normalised

        context["accounts"] = accounts

        return context

    def sim_price(self):
        # prices
        price = {}
        for asset, values in self.simulation_time.prices.items():
            price[asset.symbol] = values[self.simulation_time.timestamp]
        return price

    def sim_state(self):
        state_context = {}

        state_context["simulation_time"] = self.simulation_time.timestamp

        state_context["prices"] = self.sim_price()

        state_context["total_protocol_revenue"] = (
            self.liquidation_engine.protocol_revenue / (10**self.numeraire.decimals)
        )

        # non_liquidated_account = healthy accounts + in auction
        non_liquidated_accounts = []
        for margin_account in self.accounts:
            if (
                margin_account.address
                not in self.liquidation_engine.all_liquidated_accounts
            ):

                collateral = {}
                for asset in margin_account.assets:
                    collateral_asset_name = asset.asset.symbol
                    collateral_asset_amount = asset.metadata.amount / (
                        10**asset.asset.decimals
                    )
                    # portfolio_share = asset.metadata.share/(10**4) ## requires fix
                    portfolio_share = (
                        asset.metadata.share / (10**4)
                        if asset.metadata.share is not None
                        else 0
                    )
                    collateral[collateral_asset_name] = {
                        "amount": collateral_asset_amount,
                        "portfolio_share": portfolio_share,
                    }

                non_liquidated_accounts.append(
                    {
                        "address": margin_account.address,
                        "collateral": collateral,
                        "debt": (
                            margin_account.debt
                            / (10**margin_account.numeraire.decimals)
                        ),
                        "numeraire": margin_account.numeraire.symbol,
                    }
                )

        state_context["non_liquidated_accounts"] = non_liquidated_accounts

        auctions = {}
        for key, value in self.liquidation_engine.auction_information.items():
            auctions[key] = {
                "debt": value.start_debt / (10**value.numeraire.decimals),
                "assets": {
                    k.symbol: v.current_amount / (10**k.decimals)
                    for k, v in value.assets.items()
                },
                "nummeraire": value.numeraire.symbol,
            }
        state_context["auctions"] = auctions

        state_context["auction_to_end"] = self.liquidation_engine.auctions_to_end

        # liquidated accounts
        state_context["all_liquidated_accounts"] = (
            self.liquidation_engine.all_liquidated_accounts
        )

        return state_context

    def sim_metrics(self):
        result_context = {}

        result_context["prices"] = self.sim_price()

        non_liquidated_accounts = []
        for margin_account in self.accounts:
            if (
                margin_account.address
                not in self.liquidation_engine.all_liquidated_accounts
            ):
                non_liquidated_accounts.append(margin_account)

        # visualize_net_insolvent_value_percentage
        result_context["timestamp"] = self.simulation_time.timestamp
        result_context["total_non_liquidated_accounts"] = len(non_liquidated_accounts)
        result_context["total_active_auctions"] = len(
            self.liquidation_engine.auction_information
        )
        result_context["total_fully_liquidated_accounts"] = len(
            self.liquidation_engine.all_liquidated_accounts
        )
        result_context["total_outstanding_debt"] = sum(
            [i.debt for i in self.accounts]
        ) / (10**self.numeraire.decimals)

        # result_context["total_exposure_per_asset"]
        total_exposure_per_asset = defaultdict(int)
        bad_debt_per_asset = defaultdict(int)
        total_insolvent_value = 0
        for account in non_liquidated_accounts:
            collateral_value = 0
            for i in account.assets:
                total_exposure_per_asset[i.asset.symbol] += (
                    i.metadata.current_amount / (10**i.asset.decimals)
                ) * self.simulation_time.get_price(i.asset)
                collateral_value += (
                    (i.metadata.current_amount / (10**i.asset.decimals))
                    * self.simulation_time.get_price(i.asset)
                    * (10**self.numeraire.decimals)
                )
            if account.debt > collateral_value:
                total_insolvent_value += account.debt - collateral_value
                initial_collateral_value = 0
                prices_per_asset = {}
                for i in account.assets:
                    start_timestamp = min(self.simulation_time.prices[i.asset])
                    initial_price = self.simulation_time.prices[i.asset][start_timestamp]
                    prices_per_asset[i.asset.symbol] = (
                        i.metadata.amount / (10**i.asset.decimals)
                    ) * initial_price
                    initial_collateral_value += (
                        i.metadata.amount / (10**i.asset.decimals)
                    ) * initial_price
                for symbol, initial_worth in prices_per_asset.items():
                    bad_debt_per_asset[symbol] = (account.debt - collateral_value) * (
                        initial_worth / initial_collateral_value
                    )

        result_context["bad_debt_per_asset"] = dict(bad_debt_per_asset)
        result_context["total_exposure_per_asset"] = dict(total_exposure_per_asset)
        result_context["total_insolvent_value"] = total_insolvent_value / (
            10**self.numeraire.decimals
        )
        result_context["total_protocol_revenue"] = (
            self.liquidation_engine.protocol_revenue / (10**self.numeraire.decimals)
        )

        # position-weighted collateral ratio
        collateral_value = 0
        total_debt = 0
        for account in non_liquidated_accounts:

            if not account.address in self.liquidation_engine.auction_information:

                total_debt += account.debt
                for i in account.assets:
                    collateral_value += (
                        (i.metadata.current_amount / (10**i.asset.decimals))
                        * self.simulation_time.get_price(i.asset)
                        * (10**self.numeraire.decimals)
                    )

        try:
            result_context["position_weighted_collateral_ratio"] = (
                collateral_value / total_debt
            )
        except ZeroDivisionError:
            result_context["position_weighted_collateral_ratio"] = np.inf
        result_context["protocol_revenue_per_asset"] = dict(
            self.liquidation_engine.protocol_revenue_per_asset
        )

        return result_context

    def event_loop(self):
        db = get_mongodb_db()
        iteration = 0

        # self.log_fd.write(f"(<{self.pipeline_id}>) [PARAMS] {self.sim_params()}\n")

        param_collection = db["PARAMS"]
        param_collection.insert_one(
            {
                "orchestrator_id": str(self.orchestrator_id),
                "pipeline_id": str(self.pipeline_id),
                "data": self.sim_params(),
            }
        )
        # self.logger.info(f"(<{self.pipeline_id}>) [ACCOUNTS] {self.sim_accounts()}")
        # self.log_fd.write(f"(<{self.pipeline_id}>) [ACCOUNTS] {self.sim_accounts()}\n")
        account_collection = db["ACCOUNTS"]
        account_collection.insert_one(
            {
                "orchestrator_id": str(self.orchestrator_id),
                "pipeline_id": str(self.pipeline_id),
                "data": self.sim_accounts(),
            }
        )

        # while True:
        for t in sorted(list(list(self.simulation_time.prices.values())[0])):
            iteration += 1
            self.simulation_time.update_by_timestamp(t)

            # self.log_fd.write(
            #     f"Iteration :: {iteration} @ {self.simulation_time.timestamp}\n"
            # )
            bids_context = {}
            for liquidator in self.liquidators:
                for account in self.accounts:
                    liquidator.scan_account(account)
                bid_context = liquidator.scan_auctions()
                bids_context[liquidator.liquidator_address] = bid_context

            # self.log_fd.write(
            #     f"(<{self.pipeline_id}>) [BID] {{'simulation_time': {self.simulation_time.timestamp}, 'prices': {self.sim_price()}, 'liquidator_bids': {bids_context}}}\n"
            # )
            bid_collection = db["BID"]
            bid_collection.insert_one(
                {
                    "orchestrator_id": str(self.orchestrator_id),
                    "pipeline_id": str(self.pipeline_id),
                    "data": {
                        "simulation_time": self.simulation_time.timestamp,
                        "prices": self.sim_price(),
                        "liquidator_bids": bids_context,
                    },
                }
            )

            # self.log_fd.write(f"(<{self.pipeline_id}>) [STATE] {self.sim_state()}\n")
            # state_collection = db["STATE"]
            # state_collection.insert_one({"orchestrator_id": str(self.orchestrator_id), "pipeline_id": str(self.pipeline_id), "data": self.sim_state()})

            metrics_collection = db["METRICS"]
            metrics_collection.insert_one(
                {
                    "orchestrator_id": str(self.orchestrator_id),
                    "pipeline_id": str(self.pipeline_id),
                    "data": self.sim_metrics(),
                }
            )

            if set([a.address for a in self.accounts]) == set(
                self.liquidation_engine.all_liquidated_accounts
            ):
                self.logger.info(f"(<{self.pipeline_id}>) EARLY STOP\n")
                break
