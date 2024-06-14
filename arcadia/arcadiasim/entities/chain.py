from ..models.chain import Chain

ethereum = Chain(
    name="Ethereum",
    chain_id=1,
    rpc_url="https://eth.llamarpc.com",
    explorer_url="https://etherscan.io",
)

base = Chain(
    name="Base",
    chain_id=8453,
    rpc_url="https://mainnet.base.org",
    explorer_url="https://basescan.org/",
)
