from .base import Base
from .arcadia import AssetValueAndRiskFactors
from typing import DefaultDict, Dict, Any

# from arcadiasim.models.arcadia import MarginAccount
from ..models.asset import Asset


class SimulationMetrics(Base):
    """
    Data type related to storing metrics related to one scenario
    or simulation. Should be initiated in a liquidation engine
    """

    insolvent_accounts: int = 0
    insolvent_values_per_account: DefaultDict[str, int] = []
    insolvent_values_per_asset: DefaultDict[Asset, int] = []


# class PipelineMetadata(Base):
#     """
#     Data type related to pipeline logging related to one scenario
#     or simulation. Should be initiated at the end
#     """

#     # state_history: Dict[int, Any]
#     # bidding_history: Dict[int, Any]
#     # sim_params: DefaultDict[str, Any] = []
#     # pipeline_id: str

#     state_history: Dict[int, Any]
#     bidding_history: Dict[int, Any]
#     sim_params: Dict[str, Any]
#     pipeline_id: str
