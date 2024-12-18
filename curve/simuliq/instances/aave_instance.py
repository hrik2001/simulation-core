import dotenv
import os

from curve.simuliq.instances.chain_instance import ARBITRUM_DTO, OPTIMISM_DTO, ETHEREUM_DTO, BASE_DTO
from curve.simuliq.models.aave_protocol import AaveProtocolDTO

dotenv.load_dotenv()

# Arbitrum Instance
AaveArbitrum = AaveProtocolDTO(
    chain=ARBITRUM_DTO,
    protocol="aave",
    batch_data_provider_address=None,  # TODO: deploy and add address
    aave_pool_address="0x794a61358D6845594F94dc1DB02A252b5b4814aD",
    aave_data_provider_address="0x7F23D86Ee20D869112572136221e173428DD740B",
    holder_query_id=None  # TODO: Create query and add query id
)

# Optimism Instance
AaveOptimism = AaveProtocolDTO(
    chain=OPTIMISM_DTO,
    protocol="aave",
    batch_data_provider_address=None,  # TODO: deploy and add address
    aave_pool_address="0x794a61358D6845594F94dc1DB02A252b5b4814aD",
    aave_data_provider_address="0x7F23D86Ee20D869112572136221e173428DD740B",
    holder_query_id=None  # TODO: Create query and add query id
)

# Ethereum Instance
AaveEthereum = AaveProtocolDTO(
    chain=ETHEREUM_DTO,
    protocol="aave",
    batch_data_provider_address="0x5c438e0e82607a3a07e6726b10e200739635895b",
    aave_pool_address="0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
    aave_data_provider_address="0x41393e5e337606dc3821075Af65AeE84D7688CBD",
    holder_query_id=4101003
)

# Base Instance
AaveBase = AaveProtocolDTO(
    chain=BASE_DTO,
    protocol="aave",
    batch_data_provider_address="0x8b19901ed007558b9b58f858467789b3ba46ce5d",
    aave_pool_address="0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
    aave_data_provider_address="0xd82a47fdebB5bf5329b09441C3DaB4b5df2153Ad",
    holder_query_id=4154340
)

# Create a mapping for easy access by network
aave_protocol_mapping = {
    "arbitrum": AaveArbitrum,
    "optimism": AaveOptimism,
    "ethereum": AaveEthereum,
    "base": AaveBase
}