from dataclasses import dataclass

from core.models import Chain


@dataclass()
class ProtocolDTO:
    """
    Data Transfer Object to store relevant protocol data.
    
    Attributes:
        chain (Chain): The chain information
        protocol (str): The protocol name
    """

    chain: Chain
    protocol: str
    
    def __str__(self):
        return f"{self.protocol} on {self.chain.chain_name}"
