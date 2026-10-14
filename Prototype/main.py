import math
import random
import threading
import time
import multiprocessing as Process
import os
from concurrent.futures import ThreadPoolExecutor

# Each object represents one human or zombie.
class Human:
    def __init__(self):
        self.health = 100
        self.power = random.randint (1, 5)


class Zombie:
    def __init__(self):
        self.health = 100
        self.power = random.randint (1, 5)


# Creates a group of units in a worker thread.
def _create_unit_chunk(args):
    unit_class, count = args

    return [unit_class() for _ in range(count)]


# Distributes unit creation across worker threads.
def create_units_multithreaded(
    unit_class, count, executor, workers
):
    if count < 0:
        raise ValueError("Unit count cannot be negative.")

    if count == 0:
        return []

    chunk_count = min(workers, count)
    base_size, remainder = divmod(count, chunk_count)

    chunks = [
        (
            unit_class,
            base_size + (1 if i < remainder else 0)
        )
        for i in range(chunk_count)
    ]

    units = []

    for created_chunk in executor.map(
        _create_unit_chunk, chunks
    ):
        units.extend(created_chunk)

    return units

#Game Loop to keep the game running until the user decides to quit. The user can input the number of humans and zombies, and the game will simulate battles between them.
game_on = 1
while game_on == 1:

    #Loop to get user input for the number of humans and zombies
    choice = "i"
    while choice != "q": 
        try: 
            human_power = int(input("Enter the number of humans: "))
            zombie_power = int(input("Enter the number of zombies: "))
            if human_power < 0 or zombie_power < 0:
                print("Please enter non-negative integers for both humans and zombies.")
                continue
            choice = "q"  # Exit the loop if input is valid
        except ValueError:
            print("Invalid input. Please enter non-negative integers for both humans and zombies.")

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

    # Calculates one battle and its casualties in a worker thread.
        

    
    # Calculates one battle and its casualties in a worker thread.


    
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
    def _resolve_one_battle(human_power, zombie_power):
                battle = simulate_battle(
                human_power,
                zombie_power
        )
    
                losses = calculate_power_losses(
                    human_power,
                    zombie_power,
                    battle["result"]
                )   
    
                return battle, losses

    # Additions (Aiden)
    # This function runs an interactive game where humans and zombies battle until one side is eliminated or the battle limit is reached.
    def run_game(h_power, z_power):
    # Create one object for every unit of starting power.
        humans = [Human() for _ in range(h_power)]
        zombies = [Zombie() for _ in range(z_power)]

        max_battles = 1000
        battle_number = 0

        # Determine the number of worker threads.
        workers = min(32, os.cpu_count() or 8)

        # Create a shared pool of worker threads.
        with ThreadPoolExecutor(
            max_workers=workers
        ) as executor:

            print(
                f"Creating units using up to "
                f"{workers} worker threads..."
            )

            # Create individual human and zombie objects.
            humans = create_units_multithreaded(
                Human,
                h_power,
                executor,
                workers
            )

            zombies = create_units_multithreaded(
                Zombie,
                z_power,
                executor,
                workers
            )

            print(
                f"Starting forces — Humans: {len(humans)}, "
                f"Zombies: {len(zombies)}"
            )

            for battle_number in range(
                1, max_battles + 1
            ):
                human_power = len(humans)
                zombie_power = len(zombies)

                # Check whether either side has been eliminated.
                if human_power == 0 and zombie_power == 0:
                    print("Both sides were eliminated. It's a draw!")
                    break
                elif human_power == 0:
                    print("Zombies win!")
                    break
                elif zombie_power == 0:
                    print("Humans win!")
                    break

                # Submit the battle calculation to a worker thread.
                future = executor.submit(
                    _resolve_one_battle,
                    human_power,
                    zombie_power
                )

                # Wait for this round's results before continuing.
                battle, losses = future.result()

                # Determine how many objects must be removed.
                human_casualties = min(
                    int(losses["human_power_lost"]),
                    len(humans)
                )

                zombie_casualties = min(
                    int(losses["zombie_power_lost"]),
                    len(zombies)
                )

                # Randomly select which humans were defeated.
                if human_casualties:
                    dead_indices = set(
                        random.sample(
                            range(len(humans)),
                            human_casualties
                        )
                    )

                    humans = [
                        unit
                        for index, unit in enumerate(humans)
                        if index not in dead_indices
                    ]

                # Randomly select which zombies were defeated.
                if zombie_casualties:
                    dead_indices = set(
                        random.sample(
                            range(len(zombies)),
                            zombie_casualties
                        )
                    )

                    zombies = [
                        unit
                        for index, unit in enumerate(zombies)
                        if index not in dead_indices
                    ]

                # Display the results of this round.
                print(
                    f"Battle {battle_number}: "
                    f"{battle['winner']} won! "
                    f"Humans lost: {human_casualties}, "
                    f"Zombies lost: {zombie_casualties}, "
                    f"Remaining — Humans: {len(humans)}, "
                    f"Zombies: {len(zombies)}"
                )

            else:
                # Runs only if the maximum number of battles is reached.
                print("Battle limit reached.")

                if len(humans) > len(zombies):
                    print("Humans win!")
                elif len(zombies) > len(humans):
                    print("Zombies win!")
                else:
                    print("It's a draw!")

            print(
                f"Final forces — Humans: {len(humans)}, "
                f"Zombies: {len(zombies)}"
            )
    print("Would you like to play again? (y/n)")
    choice = input().strip().lower()
    if choice == 'y':
        game_on = 1
    else:
        game_on = 0
        print("Thank you for playing!")


    run_game(human_power, zombie_power)
print("Simulation complete. Would you like to play again? (y/n)")
user_choice = input().strip().lower()
if user_choice == 'y':
    game_on = 1
else:
    game_on = 0
    print("Thank you for playing!")
