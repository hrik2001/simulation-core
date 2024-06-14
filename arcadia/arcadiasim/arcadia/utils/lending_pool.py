from arcadia.arcadiasim.models.arcadia import LendingPoolLiquidationConfig


def calculate_rewards(config: LendingPoolLiquidationConfig, debt: int):
    one_4 = 10**4

    # Calculate initiation reward
    initiation_reward = debt * config.initiation_weight // one_4
    initiation_reward = min(initiation_reward, config.max_initiation_fee)

    # Calculate termination reward
    termination_reward = debt * config.termination_weight // one_4
    termination_reward = min(termination_reward, config.max_termination_fee)

    # Calculate liquidation penalty
    liquidation_penalty = debt * config.penalty_weight // one_4

    return initiation_reward, termination_reward, liquidation_penalty
