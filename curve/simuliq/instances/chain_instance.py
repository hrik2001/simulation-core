import dotenv
import os

dotenv.load_dotenv()

RPC_ARB=os.getenv('RPC_ARB')
RPC_OP=os.getenv('RPC_OP')
RPC_ETH="https://ethereum.blockpi.network/v1/rpc/0d2baa6393853e0ecebc7db7ee0dcb1486ac8212"
RPC_BASE=os.getenv('RPC_BASE')

# OPTIMISM_DTO = ChainDTO(
#     network="Optimism",
#     network_id=10,
#     rpc_url=RPC_OP,
#     )
#
# ARBITRUM_DTO = ChainDTO(
#     network="Arbitrum",
#     network_id=42161,
#     rpc_url=RPC_ARB,
# )
#
# ETHEREUM_DTO = ChainDTO(
#     network="Ethereum",
#     network_id=1,
#     rpc_url=RPC_ETH,
# )
#
# BASE_DTO = ChainDTO(
#     network="Base",
#     network_id=8453,
#     rpc_url=RPC_BASE,
# )

# network_mapping = {
#     OPTIMISM_DTO.network_id: OPTIMISM_DTO,
#     ARBITRUM_DTO.network_id: ARBITRUM_DTO,
#     ETHEREUM_DTO.network_id: ETHEREUM_DTO,
#     BASE_DTO.network_id: BASE_DTO
# }