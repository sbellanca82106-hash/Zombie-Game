import math
import random


# Calculates the advantage (mean) of either humans or zombies based on their respective power levels.
def calculate_advantage(human_power, zombie_power):
    # Returns a positive number if humans have the advantage, negative if zombies have the advantage, and 0 if they are equal.
    if human_power < 0 or zombie_power < 0:
        raise ValueError("Power cannot be negative.")

    # Add 1 to avoid division by zero and log(0) issues.
    population_ratio = (human_power + 1) / (zombie_power + 1)

    return math.log(population_ratio)


# Calculates the uncertainty (standard deviation) of the battle outcome based on the advantage.
def calculate_uncertainty(advantage):
    base_uncertainty = 1.5
    minimum_uncertainty = 0.3

    # Uncertainty decreases as advantage increases
    uncertainty = base_uncertainty / (
        1 + 0.6 * abs(advantage)
    )

    return max(minimum_uncertainty, uncertainty)


# Simulates a single battle round between humans and zombies.
def simulate_battle(human_power, zombie_power):

    # Calculates advantage using both sides' power levels
    advantage = calculate_advantage(
        human_power,
        zombie_power
    )

    # Calculates uncertainty based on the advantage
    uncertainty = calculate_uncertainty(advantage)

    # Results are generated using a bell curve distribution. The advantage is the mean, and the uncertainty is the standard deviation.
    result = random.gauss(
        advantage,
        uncertainty
    )

    # An advantage of 10 to 1 or greater guarantees victory for the stronger side.
    major_advantage_threshold = math.log(10)

    # Prevents random uncertainty from allowing the overwhelmingly weaker side to win.
    if advantage >= major_advantage_threshold:
        result = max(result, advantage)
    elif advantage <= -major_advantage_threshold:
        result = min(result, advantage)

    # Determine the winner based on the result
    if result > 0:
        winner = "humans"
    elif result < 0:
        winner = "zombies"
    else:
        winner = "draw"

    return {
        "winner": winner,
        "result": result,
        "advantage": advantage,
        "uncertainty": uncertainty
    }


# Since we are simulating a series of battles, there will be losses
# Depending on the result of the battle, each side will lose a percentage of their power.
def calculate_power_losses(
    human_power,
    zombie_power,
    result,
    base_loss_rate=0.12,
    margin_effect=0.08,
    wipeout_ratio=10.0
):
    """
    Calculates how much power each side loses after a battle.

    Both sides suffer the base loss rate.

    The magnitude of the result determines the margin of victory:
    - The winner loses less power.
    - The loser loses more power.
    - A close result gives both sides similar losses.
    - A decisive result creates a larger difference in losses.
    """

    # Converts any result into a bounded value from 0 to almost 1.
    # This prevents unusually large Gaussian results from causing
    # unreasonable loss percentages.
    victory_margin = math.tanh(abs(result))

    loss_rate_difference = margin_effect * victory_margin

    if result > 0:
        # Humans won.
        human_loss_rate = base_loss_rate - loss_rate_difference
        zombie_loss_rate = base_loss_rate + loss_rate_difference

    elif result < 0:
        # Zombies won.
        human_loss_rate = base_loss_rate + loss_rate_difference
        zombie_loss_rate = base_loss_rate - loss_rate_difference

    else:
        # Exact draw.
        human_loss_rate = base_loss_rate
        zombie_loss_rate = base_loss_rate

    # Wipe out zombies when victorious humans have a major power advantage.
    if (
        result > 0
        and zombie_power > 0
        and human_power / zombie_power >= wipeout_ratio
    ):
        zombie_loss_rate = 1.0

    # Wipe out humans when victorious zombies have a major power advantage.
    elif (
        result < 0
        and human_power > 0
        and zombie_power / human_power >= wipeout_ratio
    ):
        human_loss_rate = 1.0

    # Ensure loss rates cannot become negative or exceed 100%.
    human_loss_rate = max(0.0, min(1.0, human_loss_rate))
    zombie_loss_rate = max(0.0, min(1.0, zombie_loss_rate))

    human_power_lost = human_power * human_loss_rate
    zombie_power_lost = zombie_power * zombie_loss_rate

    # Convert calculated losses to whole forces before updating either side.
    human_power_lost = min(human_power, round(human_power_lost))
    zombie_power_lost = min(zombie_power, round(zombie_power_lost))

    # The losing side always loses at least one force, preventing low-force stalemates.
    if result > 0 and zombie_power > 0:
        zombie_power_lost = max(1, zombie_power_lost)
    elif result < 0 and human_power > 0:
        human_power_lost = max(1, human_power_lost)

    # Both sides lose at least one force in the event of an exact draw.
    else:
        if human_power > 0:
            human_power_lost = max(1, human_power_lost)
        if zombie_power > 0:
            zombie_power_lost = max(1, zombie_power_lost)

    # Recalculate loss rates so battle history matches the whole forces actually lost.
    human_loss_rate = (
        human_power_lost / human_power
        if human_power > 0
        else 0.0
    )
    zombie_loss_rate = (
        zombie_power_lost / zombie_power
        if zombie_power > 0
        else 0.0
    )

    return {
        "victory_margin": victory_margin,
        "human_loss_rate": human_loss_rate,
        "zombie_loss_rate": zombie_loss_rate,
        "human_power_lost": human_power_lost,
        "zombie_power_lost": zombie_power_lost
    }


def simulate_conflict(
    human_power,
    zombie_power,
    number_of_battles,
    base_loss_rate=0.12,
    margin_effect=0.08,
    elimination_threshold=0.01,
    wipeout_ratio=10.0
):
    """
    Simulates a sequence of battles.

    Power is reduced after every battle. Updated power values are
    then used to calculate the advantage in the next battle.
    """
    if human_power < 0 or zombie_power < 0:
        raise ValueError("Power cannot be negative.")

    if number_of_battles < 1:
        raise ValueError("There must be at least one battle.")

    # Validate the ratio used to determine a major advantage.
    if wipeout_ratio <= 1:
        raise ValueError("The wipeout ratio must be greater than 1.")

    current_human_power = int(human_power)
    current_zombie_power = int(zombie_power)

    battle_history = []

    for battle_number in range(1, number_of_battles + 1):
        # Stop early if one or both sides have been eliminated.
        if (
            current_human_power <= elimination_threshold
            or current_zombie_power <= elimination_threshold
        ):
            break

        starting_human_power = current_human_power
        starting_zombie_power = current_zombie_power

        battle = simulate_battle(
            human_power=starting_human_power,
            zombie_power=starting_zombie_power
        )

        losses = calculate_power_losses(
            human_power=starting_human_power,
            zombie_power=starting_zombie_power,
            result=battle["result"],
            base_loss_rate=base_loss_rate,
            margin_effect=margin_effect,
            # Pass the configurable wipeout ratio to the loss calculation.
            wipeout_ratio=wipeout_ratio
        )

        # Subtract the whole-force losses directly without rounding the remaining power for humans
        current_human_power = max(
            0,
            current_human_power - losses["human_power_lost"]
        )

        # Subtract the whole-force losses directly without rounding the remaining power for zombies
        current_zombie_power = max(
            0,
            current_zombie_power - losses["zombie_power_lost"]
        )

        battle_history.append({
            "battle_number": battle_number,
            "winner": battle["winner"],
            "result": battle["result"],
            "advantage": battle["advantage"],
            "uncertainty": battle["uncertainty"],
            "victory_margin": losses["victory_margin"],
            "starting_human_power": starting_human_power,
            "starting_zombie_power": starting_zombie_power,
            "human_loss_rate": losses["human_loss_rate"],
            "zombie_loss_rate": losses["zombie_loss_rate"],
            "human_power_lost": losses["human_power_lost"],
            "zombie_power_lost": losses["zombie_power_lost"],
            "remaining_human_power": current_human_power,
            "remaining_zombie_power": current_zombie_power
        })

    # Treat power below the threshold as eliminated.
    if current_human_power <= elimination_threshold:
        current_human_power = 0.0

    if current_zombie_power <= elimination_threshold:
        current_zombie_power = 0.0

    # Determine the final winner from remaining power.
    if current_human_power > current_zombie_power:
        final_winner = "humans"
    elif current_zombie_power > current_human_power:
        final_winner = "zombies"
    else:
        final_winner = "draw"

    return {
        "winner": final_winner,
        "battles_fought": len(battle_history),
        "starting_human_power": human_power,
        "starting_zombie_power": zombie_power,
        "remaining_human_power": current_human_power,
        "remaining_zombie_power": current_zombie_power,
        "battle_history": battle_history
    }


# Takes power from both sides and simulates battles based on the variable
# Edit these variables below
conflict = simulate_conflict(
    human_power=50,
    zombie_power=60,
    number_of_battles=100
)

# Prints the results of each battle in the conflict simulation.
for battle in conflict["battle_history"]:
    print(
        f"Battle {battle['battle_number']}: "
        f"{battle['winner']} won | "
        f"Result: {battle['result']:.3f} | "
        f"Humans lost: {battle['human_power_lost']:.2f} | "
        f"Zombies lost: {battle['zombie_power_lost']:.2f} | "
        f"Remaining: H {battle['remaining_human_power']:.2f}, "
        f"Z {battle['remaining_zombie_power']:.2f}"
    )

# Prints final results of the conflict simulation.
print(f"Final winner: {conflict['winner']}")
print(f"Battles fought: {conflict['battles_fought']}")
print(f"Human power remaining: {conflict['remaining_human_power']:.2f}")
print(f"Zombie power remaining: {conflict['remaining_zombie_power']:.2f}")
