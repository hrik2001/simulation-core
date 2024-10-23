import math

epochs_per_day = 225
slashing_exit_epoch = 36 * epochs_per_day
proportional_slashing_multiplier_bellatrix = 3
inactivity_score_bias = 4
inactivity_penalty_quotient_bellatrix = math.pow(2, 24)
validator_base_balance = 32
ethereum_supply = 120_000_000
gwei = 1_000_000_000
max_effective_balance = 32
maximum_number_of_validators = ethereum_supply / max_effective_balance
effective_balance_increment = 1
hysteresis_quotient = 4
hysteresis_downward_multiplier = 1
hysteresis_upward_multiplier = 5

def simulate_slashing(balance, staking_share, current_exit_queue_length, slashed_validator_share):
    data = []

    exit_queue_epoch_length = round(
        (current_exit_queue_length + (slashed_validator_share / 100 * staking_share / 100 * ethereum_supply / max_effective_balance)) 
        / get_churn_rate_per_epoch(staking_share))

    effective_balance = get_effective_balance(balance, max_effective_balance)
    basic_penalty = (1.0 / 32.0) * effective_balance

    correlation_penalty = 0
    leak_penalty = 0
    enter_exit_queue_epoch = -1
    leave_exit_queue_epoch = -1

    day = 0
    while leave_exit_queue_epoch == -1 or (leave_exit_queue_epoch > -1 and day < (leave_exit_queue_epoch / epochs_per_day) + 7):
        for epoch in range(epochs_per_day):
            if day * epochs_per_day > slashing_exit_epoch / 2 and correlation_penalty == 0:
                sum_slashed_validator = proportional_slashing_multiplier_bellatrix * (slashed_validator_share / 100 * staking_share / 100 * ethereum_supply)
                if sum_slashed_validator > ethereum_supply * staking_share / 100:
                    sum_slashed_validator = ethereum_supply * staking_share / 100

                correlation_penalty = math.floor(effective_balance * sum_slashed_validator / (ethereum_supply * staking_share / 100))

            if (day * epochs_per_day) + epoch == slashing_exit_epoch:
                enter_exit_queue_epoch = slashing_exit_epoch

            if enter_exit_queue_epoch > -1 and (day * epochs_per_day) + epoch == enter_exit_queue_epoch + exit_queue_epoch_length:
                leave_exit_queue_epoch = enter_exit_queue_epoch + exit_queue_epoch_length

            if leave_exit_queue_epoch == -1 and effective_balance - basic_penalty - correlation_penalty - leak_penalty < max_effective_balance:
                leak_penalty += get_inactivity_penalty_per_epoch(staking_share / 100 * ethereum_supply / 32)
                leak_penalty = round(leak_penalty, 6)

            effective_balance = get_effective_balance(balance - basic_penalty - correlation_penalty - leak_penalty, effective_balance)

        data.append([round(basic_penalty, 6), round(correlation_penalty, 6), round(leak_penalty, 6)])
        day += 1

    return data, ["basic_penalty", "correlation_penalty", "leak_penalty"], enter_exit_queue_epoch + exit_queue_epoch_length


def simulate_inactivity(staking_share, inactive_share):
    data = []

    exit_queue_epoch_length = round(((ethereum_supply * staking_share / 100 / 32) / get_churn_rate_per_epoch(staking_share)))

    day = 0
    balance = float(validator_base_balance)
    inactivity_leak_penalty = 0.0
    inactivity_base_penalty = 0.0
    inactivity_score = 0
    enter_exit_queue_epoch = -1
    leave_exit_queue_epoch = -1
    inactivity_leak_stop_epoch = -1

    effective_balance = get_effective_balance(balance, 32)

    # Determine if the inactivity leak applies or not
    inactivity_balance_stop = 0.0
    if inactive_share > 33:
        inactivity_balance_stop = validator_base_balance / 3 / inactive_share * 100
    else:
        inactivity_leak_stop_epoch = 0  # No inactivity leak to apply

    # Loop over days, with different stopping conditions
    while not ((inactivity_leak_stop_epoch == 0 and day > 730) or
               (enter_exit_queue_epoch == -1 and inactivity_leak_stop_epoch > 0 and day > (inactivity_leak_stop_epoch / epochs_per_day) + 30) or
               (leave_exit_queue_epoch > -1 and day > (leave_exit_queue_epoch / epochs_per_day) + 7)):

        for epoch in range(epochs_per_day): # Loop over epochs in day

            # Validator enters exit queue if balance falls below 16 ETH
            if enter_exit_queue_epoch == -1 and balance - inactivity_leak_penalty - inactivity_base_penalty < max_effective_balance / 2:
                enter_exit_queue_epoch = (day * epochs_per_day) + epoch

            if inactivity_leak_stop_epoch == -1:
                inactivity_score += inactivity_score_bias

                # Check if the inactivity leak should stop
                if balance - inactivity_leak_penalty - inactivity_base_penalty < inactivity_balance_stop:
                    inactivity_leak_stop_epoch = (day * epochs_per_day) + epoch
            else:
                if inactivity_score > 0:
                    inactivity_score -= 1

            if leave_exit_queue_epoch == -1 and balance - inactivity_base_penalty - inactivity_leak_penalty > 0:
                # Apply inactivity leak for epoch
                inactivity_leak_penalty += effective_balance * inactivity_score / (inactivity_score_bias * inactivity_penalty_quotient_bellatrix)
                
                # Apply basic inactivity penalty for epoch
                inactivity_base_penalty += get_inactivity_penalty_per_epoch(staking_share / 100 * ethereum_supply / 32)
                inactivity_base_penalty = round(inactivity_base_penalty, 6)

            effective_balance = get_effective_balance(balance - inactivity_base_penalty - inactivity_leak_penalty, effective_balance)

            # Exit queue if we're in it and if delay has passed
            if enter_exit_queue_epoch > -1 and leave_exit_queue_epoch == -1 and (day * epochs_per_day) > enter_exit_queue_epoch + exit_queue_epoch_length:
                if inactivity_leak_stop_epoch == -1:
                    inactivity_leak_stop_epoch = (day * epochs_per_day) + epoch
                leave_exit_queue_epoch = (day * epochs_per_day) + epoch

        data.append([round(inactivity_leak_penalty, 6), round(inactivity_base_penalty, 6)])

        day += 1

    return data, ["inactivity_basic_penalty", "inactivity_leak_penalty"], enter_exit_queue_epoch, leave_exit_queue_epoch, inactivity_leak_stop_epoch



# getChurnRatePerEpoch returns the churn rate per epoch based on the staking share.
def get_churn_rate_per_epoch(staking_share):
    validator_count = ethereum_supply * staking_share / 100 / max_effective_balance
    if validator_count < 65536:
        return 4
    return 4 + ((validator_count - 65536) / 65536)

# getInactivityPenaltyPerEpoch calculates the inactivity penalty per epoch based on the number of validators.
def get_inactivity_penalty_per_epoch(validator_count):
    return 1280 / math.sqrt(32 * gwei * validator_count)

# getEffectiveBalance returns the effective balance of a validator.
def get_effective_balance(actual_balance, previous_effective_balance):
    hysteresis_increment = effective_balance_increment / hysteresis_quotient
    downward_threshold = hysteresis_increment * hysteresis_downward_multiplier
    upward_threshold = hysteresis_increment * hysteresis_upward_multiplier

    if actual_balance + downward_threshold < previous_effective_balance or previous_effective_balance + upward_threshold < actual_balance:
        return min(actual_balance - math.fmod(actual_balance, effective_balance_increment), max_effective_balance)
    return previous_effective_balance

