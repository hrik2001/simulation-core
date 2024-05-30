from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class PricingMetadata(BaseModel):
    """
    Data model to implement pricing related metadata
    Used internally by the pricing module

    Check arcadiasim/pricing/pricing.py and
    aracadiasim/pricing/historical_pricing.py for further info
    """

    strategy: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
