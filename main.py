import math
import random
import threading
import time
import multiprocessing as Process
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import database_functions as db_functions
from connection import database_connect

# Each object represents one human or zombie.
class Human:
    def __init__(self):
        self.agent_id = None
        self.health = 100
        self.power = random.randint (1, 5)
        # The simulation currently battles by population count, so these
        # stored attributes use the database schema's existing defaults.
        self.speed = 1
        self.weapon_tier = 1
        self.x_pos = 0
        self.y_pos = 0


class Zombie:
    def __init__(self):
        self.agent_id = None
        self.health = 100
        self.power = random.randint (1, 5)
        self.speed = 1
        self.strength = 1
        self.x_pos = 0
        self.y_pos = 0


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

# Shared grid and perception settings. Coordinates are integer grid cells.
GRID_WIDTH = 100
GRID_HEIGHT = 100
DETECTION_RADIUS = 10.0  # Euclidean distance measured in grid cells.
MOVEMENT_RNG = random.Random()  # Keep movement randomness separate from battle outcomes.


def assign_initial_grid_positions(humans, zombies):
    """Give every agent a grid coordinate; avoid overlaps when practical."""
    agents = list(humans) + list(zombies)
    if not agents:
        return

    total_cells = GRID_WIDTH * GRID_HEIGHT
    cell_ids = list(range(total_cells))
    MOVEMENT_RNG.shuffle(cell_ids)

    # Each agent starts in a different cell unless the population exceeds the grid.
    if len(agents) <= total_cells:
        chosen_cells = cell_ids[:len(agents)]
    else:
        chosen_cells = cell_ids + [
            MOVEMENT_RNG.randrange(total_cells)
            for _ in range(len(agents) - total_cells)
        ]

    for agent, cell_id in zip(agents, chosen_cells):
        agent.x_pos = cell_id % GRID_WIDTH
        agent.y_pos = cell_id // GRID_WIDTH


def _grid_distance(position_a, position_b):
    """Return Euclidean distance between two grid cells."""
    return math.hypot(
        position_a[0] - position_b[0],
        position_a[1] - position_b[1],
    )


def _roam_to_neighbor(x_pos, y_pos):
    """Move to a random adjacent cell while staying inside the grid."""
    neighbors = [
        (x_pos + dx, y_pos + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if (dx != 0 or dy != 0)
        and 0 <= x_pos + dx < GRID_WIDTH
        and 0 <= y_pos + dy < GRID_HEIGHT
    ]
    # Every grid cell has at least one valid neighbor for this grid size.
    return MOVEMENT_RNG.choice(neighbors)


def _next_agent_position(agent, opposing_agents, old_positions, detection_radius):
    """Chase the closest opposing agent in range; otherwise roam randomly."""
    current = old_positions[id(agent)]

    if opposing_agents:
        target = min(
            opposing_agents,
            key=lambda opponent: _grid_distance(
                current, old_positions[id(opponent)]
            ),
        )
        target_position = old_positions[id(target)]
        distance = _grid_distance(current, target_position)

        if distance <= detection_radius and target_position != current:
            target_x, target_y = target_position
            x_pos, y_pos = current
            # One step per battle; diagonal movement is allowed.
            next_x = x_pos + ((target_x > x_pos) - (target_x < x_pos))
            next_y = y_pos + ((target_y > y_pos) - (target_y < y_pos))
            return (
                max(0, min(GRID_WIDTH - 1, next_x)),
                max(0, min(GRID_HEIGHT - 1, next_y)),
            )

    # No opposing agent in range (or agents already share a cell): keep roaming.
    return _roam_to_neighbor(*current)


def move_agents_for_battle(humans, zombies, detection_radius=DETECTION_RADIUS):
    """Move all agents once, using a snapshot so movement is simultaneous.

    Humans only sense/chase zombies. Zombies only sense/chase humans. An agent
    with no opponent within detection_radius roams to a random neighboring cell.
    """
    if not humans or not zombies:
        return

    all_agents = list(humans) + list(zombies)
    old_positions = {
        id(agent): (agent.x_pos, agent.y_pos)
        for agent in all_agents
    }
    planned_moves = []

    for human in humans:
        planned_moves.append((
            human,
            _next_agent_position(human, zombies, old_positions, detection_radius),
        ))

    for zombie in zombies:
        planned_moves.append((
            zombie,
            _next_agent_position(zombie, humans, old_positions, detection_radius),
        ))

    # Apply moves only after all next positions were computed from old positions.
    for agent, (new_x, new_y) in planned_moves:
        agent.x_pos = new_x
        agent.y_pos = new_y


class SimulationRecorder:
    """Writes simulation events to PostgreSQL without ever stopping the game.

    Every event is its own committed transaction. If a write fails, the error
    is printed, the connection is re-opened once, and the write is retried, so
    one transient problem no longer switches saving off for the whole run.
    """

    def __init__(self):
        self.conn = None
        self.simulation_id = None

    def _connect(self):
        self.close()
        self.conn = database_connect()
        # Creates missing tables/columns. If this fails (for example the
        # connected user does not own the tables), keep going: the tables may
        # already be fine, and real insert errors will be reported below.
        try:
            db_functions.ensure_schema(self.conn)
            self.conn.commit()
        except Exception as exc:
            self.conn.rollback()
            print(
                f"Warning: schema check skipped ({exc}). Continuing with existing tables.",
                file=sys.stderr,
            )

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = None

    def _write(self, label, action):
        """Run action(conn) as one transaction; retry once after reconnecting."""
        for attempt in (1, 2):
            if self.conn is None:
                return False
            try:
                action(self.conn)
                self.conn.commit()
                return True
            except Exception as exc:
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                print(
                    f"Warning: database write failed ({label}, attempt {attempt}): {exc}",
                    file=sys.stderr,
                )
                if attempt == 1:
                    try:
                        self._connect()
                    except Exception as reconnect_exc:
                        print(
                            f"Warning: could not reconnect to PostgreSQL: {reconnect_exc}",
                            file=sys.stderr,
                        )
                        break
        self.close()
        print(
            "Warning: PostgreSQL saving is now disabled for the rest of this run.",
            file=sys.stderr,
        )
        return False

    def _describe_target(self):
        """Print exactly which database is being written to."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT current_database(), current_user, "
                    "COALESCE(inet_server_addr()::text, 'local socket'), "
                    "inet_server_port();"
                )
                dbname, user, host, port = cur.fetchone()
            self.conn.commit()
            print(f"Database: '{dbname}' as '{user}' on {host}:{port}")
        except Exception as exc:
            self.conn.rollback()
            print(f"Warning: could not identify the database: {exc}", file=sys.stderr)

    def _count_saved_agents(self):
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM agents WHERE simulation_id = %s;",
                    (self.simulation_id,),
                )
                total = cur.fetchone()[0]
            self.conn.commit()
            return total
        except Exception as exc:
            self.conn.rollback()
            print(f"Warning: could not verify saved agents: {exc}", file=sys.stderr)
            return None

    def start(self, humans, zombies):
        """Create the simulation row, then insert and commit each agent as it is created."""
        try:
            self._connect()
        except Exception as exc:
            self.close()
            print(f"WARNING: could not connect to PostgreSQL; this run will NOT be saved: {exc}")
            return

        self._describe_target()

        def create_sim(conn):
            self.simulation_id = db_functions.create_simulation(
                conn,
                starting_humans=len(humans),
                starting_zombies=len(zombies),
            )

        if not self._write("create simulation", create_sim):
            print("WARNING: could not create the simulation row; this run will NOT be saved.")
            return

        agents = [("human", h) for h in humans] + [("zombie", z) for z in zombies]
        saved = 0
        for kind, agent in agents:
            def create_agent(conn, kind=kind, agent=agent):
                if kind == "human":
                    agent.agent_id = db_functions.create_human(
                        agent.health, agent.speed, agent.weapon_tier,
                        agent.x_pos, agent.y_pos, conn,
                        simulation_id=self.simulation_id, power=agent.power,
                    )
                else:
                    agent.agent_id = db_functions.create_zombie(
                        agent.health, agent.speed, agent.strength,
                        agent.x_pos, agent.y_pos, conn,
                        simulation_id=self.simulation_id, power=agent.power,
                    )

            # Each agent is committed on its own, so it is visible in the
            # database as soon as it has been created.
            if self._write(f"create {kind}", create_agent):
                saved += 1
            elif self.conn is None:
                break

        stored = self._count_saved_agents()
        print(
            f"Saved simulation {self.simulation_id}: inserted {saved} of {len(agents)} agents"
            + (f"; database confirms {stored} agents for this simulation." if stored is not None else ".")
        )

    def record_positions(self, humans, zombies):
        """Event: agents moved."""
        self._write(
            "positions",
            lambda conn: db_functions.update_agent_positions(conn, humans, zombies),
        )

    def record_deaths(self, dead_agents):
        """Event: agents were defeated."""
        if dead_agents:
            self._write(
                "casualties",
                lambda conn: db_functions.mark_agents_dead(conn, dead_agents),
            )

    def finish(self):
        """Mark the simulation finished and release the connection."""
        if self.conn is not None and self.simulation_id is not None:
            self._write(
                "finish simulation",
                lambda conn: db_functions.finish_simulation(conn, self.simulation_id),
            )
        self.close()


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
        max_battles = 1000
        workers = min(32, os.cpu_count() or 8)
        recorder = SimulationRecorder()

        try:
            # Keep using the existing worker pool for agent construction.
            with ThreadPoolExecutor(max_workers=workers) as executor:
                print(
                    f"Creating units using up to "
                    f"{workers} worker threads..."
                )

                humans = create_units_multithreaded(
                    Human, h_power, executor, workers
                )
                zombies = create_units_multithreaded(
                    Zombie, z_power, executor, workers
                )

                # Place all starting agents on the grid before writing them.
                assign_initial_grid_positions(humans, zombies)

                # Event: agents created -> insert each one into PostgreSQL.
                recorder.start(humans, zombies)

                print(
                    f"Starting forces — Humans: {len(humans)}, "
                    f"Zombies: {len(zombies)}"
                )

                for battle_number in range(1, max_battles + 1):
                    human_power = len(humans)
                    zombie_power = len(zombies)

                    # Keep the original end-of-battle conditions and messages.
                    if human_power == 0 and zombie_power == 0:
                        print("Both sides were eliminated. It's a draw!")
                        break
                    elif human_power == 0:
                        print("Zombies win!")
                        break
                    elif zombie_power == 0:
                        print("Humans win!")
                        break

                    # Every surviving agent moves once before this battle.
                    move_agents_for_battle(humans, zombies)

                    # Event: agents moved -> update their rows.
                    recorder.record_positions(humans, zombies)

                    # Submit the existing battle calculation to a worker thread.
                    future = executor.submit(
                        _resolve_one_battle,
                        human_power,
                        zombie_power,
                    )
                    battle, losses = future.result()

                    human_casualties = min(
                        int(losses["human_power_lost"]), len(humans)
                    )
                    zombie_casualties = min(
                        int(losses["zombie_power_lost"]), len(zombies)
                    )

                    dead_humans = []
                    dead_zombies = []

                    # Randomly select and track which humans were defeated.
                    if human_casualties:
                        dead_indices = set(
                            random.sample(range(len(humans)), human_casualties)
                        )
                        dead_humans = [
                            unit for index, unit in enumerate(humans)
                            if index in dead_indices
                        ]
                        humans = [
                            unit for index, unit in enumerate(humans)
                            if index not in dead_indices
                        ]

                    # Randomly select and track which zombies were defeated.
                    if zombie_casualties:
                        dead_indices = set(
                            random.sample(range(len(zombies)), zombie_casualties)
                        )
                        dead_zombies = [
                            unit for index, unit in enumerate(zombies)
                            if index in dead_indices
                        ]
                        zombies = [
                            unit for index, unit in enumerate(zombies)
                            if index not in dead_indices
                        ]

                    # Event: agents defeated -> mark them dead (health 0).
                    recorder.record_deaths(dead_humans + dead_zombies)

                    # Preserve the original battle output format.
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
        finally:
            # Mark the run as finished and always release the DB connection.
            recorder.finish()

    # Finish this simulation before asking whether to start another one.
    run_game(human_power, zombie_power)

    print("Would you like to play again? (y/n)")
    choice = input().strip().lower()
    if choice == 'y':
        game_on = 1
    else:
        game_on = 0
        print("Thank you for playing!")
