from pydantic import BaseModel


class Chain(BaseModel):
    """
    Data model for an EVM compatible chain
    """

    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
