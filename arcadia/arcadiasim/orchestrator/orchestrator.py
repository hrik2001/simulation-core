import os
from multiprocessing import Pool
from itertools import product
from collections import defaultdict
from typing import List, Dict, Any, Optional
from copy import deepcopy
import logging
import pickle
from ..logging import (
    multiprocessing_logging_queue,
    CUSTOM_LOGGING_CONFIG,
    get_logger,
)

from ..models.asset import Asset
from ..models.base import Base
from ..models.time import SimulationTime
from ..arcadia.liquidation_engine import LiquidationEngine
from ..arcadia.liquidator import Liquidator
from ..pipeline.pipeline import Pipeline
from ..models.arcadia import (
    MarginAccount,
    AssetsInMarginAccount,
    AssetMetadata,
    AssetValueAndRiskFactors,
    Ranges,
)
import uuid
from ..utils import get_mongodb_db


class Orchestrator(Base):
    """
    Brute force implementation of orchestrator, has no optimization
    """

    start_timestamp: int
    end_timestamp: int
    simulation_time: SimulationTime
    liquidation_engine: LiquidationEngine
    liquidators: List[Liquidator]
    no_of_margin_accounts: int
    # asset: Asset
    # asset_ranges: Ranges
    debt_init_model: Any
    asset_ranges: Dict[Asset, Ranges]
    # exposure_range: range | list
    numeraire: Asset
    logging_queue: Optional[Any] = None
    pipeline_reruns: int = 1
    orchestrator_id: Optional[uuid.UUID] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logging.config.dictConfig(CUSTOM_LOGGING_CONFIG)

        self.logger = get_logger(__name__)

    def prepare_simulation(self):

        global_parameter_set = []
        orchestrator_id = uuid.uuid4()
        self.orchestrator_id = orchestrator_id

        for _ in range(self.pipeline_reruns):
            parameter_sets = []

            assets_in_margin_account = defaultdict(list)
            for asset, asset_ranges in self.asset_ranges.items():
                config_list = product(
                    asset_ranges.collateral_factor_range,
                    asset_ranges.liquidation_factor_range,
                    asset_ranges.exposure_range,
                )

                # config_list = list(filter(lambda i: i[1] > i[0], config_list))
                P_i = self.simulation_time.prices[asset][self.start_timestamp]
                P_min = min(self.simulation_time.prices[asset].values())
                config_list = list(
                    filter(lambda i: (i[0] / i[1]) >= (P_min / P_i), config_list)
                )
                config_list = list(filter(lambda i: i[1] > i[0], config_list))

                # print((P_min/P_i), (P_min, P_i))

                for config in config_list:
                    assets_in_margin_account[asset].append(
                        AssetsInMarginAccount(
                            asset=asset,
                            metadata=AssetMetadata(
                                amount=0,
                                current_amount=0,
                                risk_metadata=AssetValueAndRiskFactors(
                                    collateral_factor=config[0],
                                    liquidation_factor=config[1],
                                    exposure=config[2],
                                ),
                            ),
                        )
                    )

            scenarios = list(product(*list(assets_in_margin_account.values())))

            # _account_metadata = [all_asset_combinations for _ in range(self.no_of_margin_accounts)]

            # all_account_combinations_in_scenario = product(*_account_metadata)

            for scenario in scenarios:
                accounts = []
                prices = {
                    asset: self.simulation_time.prices[asset][self.start_timestamp]
                    for asset in self.simulation_time.prices
                }
                account_metadata = [
                    deepcopy(list(scenario)) for _ in range(self.no_of_margin_accounts)
                ]
                exposure = {
                    collateral_asset_metadata.asset: collateral_asset_metadata.metadata.risk_metadata.exposure
                    for collateral_asset_metadata in scenario
                }
                # TODO: no exposure for now, since the models don't support it
                account_init_data = self.debt_init_model(
                    exposure, prices, account_metadata, self.numeraire
                )
                for index, assets in enumerate(account_metadata):
                    debt = account_init_data[index].debt
                    account = MarginAccount(
                        address=f"0xTest{index}",
                        debt=int(debt * (10**self.numeraire.decimals)),
                        numeraire=self.numeraire,
                        assets=assets,
                    )
                    accounts.append(account)

                parameter_sets.append(
                    (
                        self.start_timestamp,
                        self.end_timestamp,
                        self.simulation_time,
                        self.liquidation_engine,
                        self.liquidators,
                        accounts,
                        orchestrator_id,
                        self.numeraire,
                    )
                )

            # return parameter_sets
            global_parameter_set += parameter_sets
        return global_parameter_set

    @staticmethod
    def worker(params):

        (
            start_timestamp,
            end_timestamp,
            sim_time,
            liquidation_engine,
            liquidators,
            accounts,
            orchestrator_id,
            numeraire,
            logging_queue,
        ) = params

        pipeline = Pipeline(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            simulation_time=sim_time,
            liquidation_engine=liquidation_engine,
            liquidators=liquidators,
            accounts=accounts,
            numeraire=numeraire,
            logging_queue=logging_queue,
            pipeline_id=uuid.uuid4(),
            orchestrator_id=orchestrator_id,
        )

        pipeline.event_loop()

    def sim_orchestrator(self):
        sim_context = {}
        sim_context["start_timestamp"] = self.start_timestamp
        sim_context["end_timestamp"] = self.end_timestamp
        sim_context["number_of_accounts"] = self.no_of_margin_accounts
        sim_context["number_of_liquidators"] = len(self.liquidators)

        # liquidator
        liquidator_dict = {}
        for liquidator in self.liquidators:
            liquidator_dict[liquidator.liquidator_address] = {
                "balance": liquidator.balance
            }
        sim_context["liquidators"] = liquidator_dict

        # Liquidation Engine
        liquidation_engine_config = {}
        liquidation_engine_config["base"] = (
            self.liquidation_engine.liquidation_config.base
        )
        liquidation_engine_config["maximum_auction_duration"] = (
            self.liquidation_engine.liquidation_config.maximum_auction_duration
        )
        liquidation_engine_config["start_price_multiplier"] = (
            self.liquidation_engine.liquidation_config.start_price_multiplier
        )
        liquidation_engine_config["min_price_multiplier"] = (
            self.liquidation_engine.liquidation_config.min_price_multiplier
        )
        liquidation_engine_config["lending_pool"] = dict(
            self.liquidation_engine.liquidation_config.lending_pool
        )
        sim_context["liquidation_engine"] = liquidation_engine_config

        # simulation_time
        ## TO-DO: Include logging for simulation_time

        sim_context["debt_init_model"] = f"{self.debt_init_model.__name__}"

        # asset ranges
        asset_ranges_config = {}
        for key, value in self.asset_ranges.items():
            asset_normalised = {}
            asset_normalised["collateral_factor_range"] = list(
                dict(value)["collateral_factor_range"]
            )
            asset_normalised["liquidation_factor_range"] = list(
                dict(value)["liquidation_factor_range"]
            )
            asset_normalised["exposure_range"] = [
                i / (10**key.decimals) for i in list(dict(value)["exposure_range"])
            ]
            asset_ranges_config[key.symbol] = asset_normalised
        sim_context["asset_ranges"] = asset_ranges_config

        sim_context["numeraire"] = self.numeraire.symbol
        sim_context["pipeline_reruns"] = self.pipeline_reruns
        return sim_context

    def execute(self):

        db = get_mongodb_db()
        with multiprocessing_logging_queue() as logging_queue:

            self.logger.info(f"[ORCHESTRATOR] {self.sim_orchestrator()}")

            with Pool(os.cpu_count()) as pool:

                params = self.prepare_simulation()
                params = [(*i, logging_queue) for i in params]
                results = pool.imap_unordered(Orchestrator.worker, params)

                for result in results:
                    print(result)

        directory = os.path.join("pipeline_logs", str(self.orchestrator_id))
        os.makedirs(directory, exist_ok=True)
        self.log_fd = open(os.path.join(directory, "orchestrator.log"), "w")
        self.log_fd.write(f"[ORCHESTRATOR] {self.sim_orchestrator()}")
        orchestrator_collection = db["ORCHESTRATOR"]
        orchestrator_collection.insert_one(
            {
                "orchestrator_id": str(self.orchestrator_id),
                "data": self.sim_orchestrator(),
            }
        )


class OrchestratorSensitivity(Base):
    """
    Brute force implementation of orchestrator, has no optimization
    """

    start_timestamp: int
    end_timestamp: int
    simulation_time: SimulationTime
    liquidation_engine: LiquidationEngine
    liquidators: List[Liquidator]
    no_of_margin_accounts: int
    # asset: Asset
    # asset_ranges: Ranges
    debt_init_model: Any
    asset_ranges: Dict[Asset, Ranges]
    # exposure_range: range | list
    numeraire: Asset
    logging_queue: Optional[Any] = None
    pipeline_reruns: int = 1
    orchestrator_id: Optional[uuid.UUID] = None
    sensitivity_interval_division: int = 5

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logging.config.dictConfig(CUSTOM_LOGGING_CONFIG)

        self.logger = get_logger(__name__)

    def prepare_simulation(self):

        global_parameter_set = []
        orchestrator_id = uuid.uuid4()
        self.orchestrator_id = orchestrator_id

        for _ in range(self.pipeline_reruns):
            parameter_sets = []

            assets_in_margin_account = defaultdict(list)
            for asset, asset_ranges in self.asset_ranges.items():
                P_i = self.simulation_time.prices[asset][self.start_timestamp]
                P_min = min(self.simulation_time.prices[asset].values())
                delta = (P_i - P_min) / (self.sensitivity_interval_division * P_i)
                base_sensitivity = P_min / P_i
                l_range = []
                for i in range(self.sensitivity_interval_division):
                    l_range.append(base_sensitivity + (i * delta))
                asset_ranges.liquidation_factor_range = l_range
                # print(f"{l_range=}")
                config_list = product(
                    asset_ranges.collateral_factor_range,
                    asset_ranges.liquidation_factor_range,
                    asset_ranges.exposure_range,
                )

                for config in config_list:
                    assets_in_margin_account[asset].append(
                        AssetsInMarginAccount(
                            asset=asset,
                            metadata=AssetMetadata(
                                amount=0,
                                current_amount=0,
                                risk_metadata=AssetValueAndRiskFactors(
                                    collateral_factor=config[0],
                                    liquidation_factor=config[0] / config[1],
                                    exposure=config[2],
                                ),
                            ),
                        )
                    )

            scenarios = list(product(*list(assets_in_margin_account.values())))

            # _account_metadata = [all_asset_combinations for _ in range(self.no_of_margin_accounts)]

            # all_account_combinations_in_scenario = product(*_account_metadata)

            for scenario in scenarios:
                accounts = []
                prices = {
                    asset: self.simulation_time.prices[asset][self.start_timestamp]
                    for asset in self.simulation_time.prices
                }
                account_metadata = [
                    deepcopy(list(scenario)) for _ in range(self.no_of_margin_accounts)
                ]
                exposure = {
                    collateral_asset_metadata.asset: collateral_asset_metadata.metadata.risk_metadata.exposure
                    for collateral_asset_metadata in scenario
                }
                # TODO: no exposure for now, since the models don't support it
                account_init_data = self.debt_init_model(
                    exposure, prices, account_metadata, self.numeraire
                )
                for index, assets in enumerate(account_metadata):
                    debt = account_init_data[index].debt
                    account = MarginAccount(
                        address=f"0xTest{index}",
                        debt=int(debt * (10**self.numeraire.decimals)),
                        numeraire=self.numeraire,
                        assets=assets,
                    )
                    accounts.append(account)

                parameter_sets.append(
                    (
                        self.start_timestamp,
                        self.end_timestamp,
                        self.simulation_time,
                        self.liquidation_engine,
                        self.liquidators,
                        accounts,
                        orchestrator_id,
                        self.numeraire,
                    )
                )

            # return parameter_sets
            global_parameter_set += parameter_sets
        return global_parameter_set

    @staticmethod
    def worker(params):

        (
            start_timestamp,
            end_timestamp,
            sim_time,
            liquidation_engine,
            liquidators,
            accounts,
            orchestrator_id,
            numeraire,
            logging_queue,
        ) = params

        pipeline = Pipeline(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            simulation_time=sim_time,
            liquidation_engine=liquidation_engine,
            liquidators=liquidators,
            accounts=accounts,
            numeraire=numeraire,
            logging_queue=logging_queue,
            pipeline_id=uuid.uuid4(),
            orchestrator_id=orchestrator_id,
        )

        pipeline.event_loop()

    def sim_orchestrator(self):
        sim_context = {}
        sim_context["start_timestamp"] = self.start_timestamp
        sim_context["end_timestamp"] = self.end_timestamp
        sim_context["number_of_accounts"] = self.no_of_margin_accounts
        sim_context["number_of_liquidators"] = len(self.liquidators)

        # liquidator
        liquidator_dict = {}
        for liquidator in self.liquidators:
            liquidator_dict[liquidator.liquidator_address] = {
                "balance": liquidator.balance
            }
        sim_context["liquidators"] = liquidator_dict

        # Liquidation Engine
        liquidation_engine_config = {}
        liquidation_engine_config["base"] = (
            self.liquidation_engine.liquidation_config.base
        )
        liquidation_engine_config["maximum_auction_duration"] = (
            self.liquidation_engine.liquidation_config.maximum_auction_duration
        )
        liquidation_engine_config["start_price_multiplier"] = (
            self.liquidation_engine.liquidation_config.start_price_multiplier
        )
        liquidation_engine_config["min_price_multiplier"] = (
            self.liquidation_engine.liquidation_config.min_price_multiplier
        )
        liquidation_engine_config["lending_pool"] = dict(
            self.liquidation_engine.liquidation_config.lending_pool
        )
        sim_context["liquidation_engine"] = liquidation_engine_config

        # simulation_time
        ## TO-DO: Include logging for simulation_time

        sim_context["debt_init_model"] = f"{self.debt_init_model.__name__}"

        # asset ranges
        asset_ranges_config = {}
        for key, value in self.asset_ranges.items():
            asset_normalised = {}
            asset_normalised["collateral_factor_range"] = list(
                dict(value)["collateral_factor_range"]
            )
            asset_normalised["liquidation_factor_range"] = list(
                dict(value)["liquidation_factor_range"]
            )
            asset_normalised["exposure_range"] = [
                i / (10**key.decimals) for i in list(dict(value)["exposure_range"])
            ]
            asset_ranges_config[key.symbol] = asset_normalised
        sim_context["asset_ranges"] = asset_ranges_config

        sim_context["numeraire"] = self.numeraire.symbol
        sim_context["pipeline_reruns"] = self.pipeline_reruns
        return sim_context

    def execute(self):

        db = get_mongodb_db()
        with multiprocessing_logging_queue() as logging_queue:

            with Pool(os.cpu_count()) as pool:

                params = self.prepare_simulation()
                self.logger.info(f"[ORCHESTRATOR] {self.sim_orchestrator()}")
                params = [(*i, logging_queue) for i in params]
                results = pool.imap_unordered(Orchestrator.worker, params)

                for result in results:
                    print(result)

        directory = os.path.join("pipeline_logs", str(self.orchestrator_id))
        os.makedirs(directory, exist_ok=True)
        self.log_fd = open(os.path.join(directory, "orchestrator.log"), "w")
        self.log_fd.write(f"[ORCHESTRATOR] {self.sim_orchestrator()}")
        orchestrator_collection = db["ORCHESTRATOR"]
        orchestrator_collection.insert_one(
            {
                "orchestrator_id": str(self.orchestrator_id),
                "data": self.sim_orchestrator(),
            }
        )
