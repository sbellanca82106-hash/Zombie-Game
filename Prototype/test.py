import math
import random
# ============================================================
#Mack contribution
class Entity:
    #Base class shared by Human and Zombie
    def __init__(self, name, health, speed, power):
        self.name = name #stores entity names
        self.health = health #stores entity health
        self.speed = speed #stores entity speed
        self.power = power #stores entity power

    def is_alive(self):
        return self.health > 0 #check if entity is alive or not

    def take_damage(self, amount):
        self.health = max(0, self.health - amount) #calculates damage taken, floored at 0 to prevent negative health


class Human(Entity): #human class details
    def __init__(self, name):
        super().__init__(name, health=10, speed=random.randint(3, 7), power=random.randint(3, 5))
        #stats for human class entity's, with randomized speed and power for simulation variance


class Zombie(Entity): #zombie class details
    def __init__(self, name):
        super().__init__(name, health=20, speed=random.randint(1, 4), power=5)
        #stats for zombie class entity's, with randomized speed for simulation variance

#AI was used for following definition, with explanation provided by AI after
def create_population(cls, count, prefix):
    # A helper function for generating a whole list of entities at once,
    # instead of writing them out one by one.
    # cls: the class to build instances of (Human or Zombie — classes can be passed like values).
    # count: how many instances to create.
    # prefix: text to put before each instance's number, e.g. "Human" or "Zombie".
    return [cls(f"{prefix}{i+1}") for i in range(count)] 
    # A list comprehension — shorthand for a loop that builds a list.
    # range(count): produces 0, 1, 2, ... up to count-1.
    # for i in range(count): loops through each of those numbers.
    # f"{prefix}{i+1}": builds a name string like "Human1", "Human2", using i+1
    #   so numbering starts at 1 instead of 0.
    # cls(...): calls the class's constructor (Human(...) or Zombie(...)) with that name.
    # The [...] around the whole expression collects every result into one list.
# ============================================================


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

    uncertainty = base_uncertainty / (
        1 + 0.6 * abs(advantage)
    )

    return max(minimum_uncertainty, uncertainty)


# Simulates a single battle round between humans and zombies.
def simulate_battle(human_power, zombie_power):

    advantage = calculate_advantage(
        human_power,
        zombie_power
    )

    uncertainty = calculate_uncertainty(advantage)

    result = random.gauss(
        advantage,
        uncertainty
    )

    major_advantage_threshold = math.log(10)

    if advantage >= major_advantage_threshold:
        result = max(result, advantage)
    elif advantage <= -major_advantage_threshold:
        result = min(result, advantage)

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


def calculate_power_losses(
    human_power,
    zombie_power,
    result,
    base_loss_rate=0.12,
    margin_effect=0.08,
    wipeout_ratio=10.0
):
    victory_margin = math.tanh(abs(result))
    loss_rate_difference = margin_effect * victory_margin

    if result > 0:
        human_loss_rate = base_loss_rate - loss_rate_difference
        zombie_loss_rate = base_loss_rate + loss_rate_difference
    elif result < 0:
        human_loss_rate = base_loss_rate + loss_rate_difference
        zombie_loss_rate = base_loss_rate - loss_rate_difference
    else:
        human_loss_rate = base_loss_rate
        zombie_loss_rate = base_loss_rate

    if (
        result > 0
        and zombie_power > 0
        and human_power / zombie_power >= wipeout_ratio
    ):
        zombie_loss_rate = 1.0
    elif (
        result < 0
        and human_power > 0
        and zombie_power / human_power >= wipeout_ratio
    ):
        human_loss_rate = 1.0

    human_loss_rate = max(0.0, min(1.0, human_loss_rate))
    zombie_loss_rate = max(0.0, min(1.0, zombie_loss_rate))

    human_power_lost = human_power * human_loss_rate
    zombie_power_lost = zombie_power * zombie_loss_rate

    human_power_lost = min(human_power, round(human_power_lost))
    zombie_power_lost = min(zombie_power, round(zombie_power_lost))

    if result > 0 and zombie_power > 0:
        zombie_power_lost = max(1, zombie_power_lost)
    elif result < 0 and human_power > 0:
        human_power_lost = max(1, human_power_lost)
    else:
        if human_power > 0:
            human_power_lost = max(1, human_power_lost)
        if zombie_power > 0:
            zombie_power_lost = max(1, zombie_power_lost)

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


# ============================================================
#Mack contribution
def losses_to_population(population, power_lost):
    remaining_loss = power_lost
    random.shuffle(population)

    for entity in population:
        if remaining_loss <= 0:
            break
        damage = min(entity.health, remaining_loss)
        entity.take_damage(damage)
        remaining_loss -= damage

    # Remove anyone who died from this round of losses.
    return [e for e in population if e.is_alive()]
# ============================================================


def simulate_conflict(#edited to to fit new class definitions
    humans,
    zombies,
    number_of_battles,
    base_loss_rate=0.12,
    margin_effect=0.08,
    elimination_threshold=0.01,
    wipeout_ratio=10.0
):
    """
    Simulates a sequence of battles between two populations
    of Human/Zombie objects (instead of raw power numbers).
    """

    # Mack edit: power is now derived from the actual population's
    # combined health, instead of being passed in directly.
    if len(humans) == 0 or len(zombies) == 0:
        raise ValueError("Both populations must start with at least one member.")

    if number_of_battles < 1:
        raise ValueError("There must be at least one battle.")

    if wipeout_ratio <= 1:
        raise ValueError("The wipeout ratio must be greater than 1.")

    battle_history = []

    for battle_number in range(1, number_of_battles + 1):
        if not humans or not zombies:
            #Mack change: New check added here at the top of the loop.
            # Needed because current_human_power/current_zombie_power get calculated further down now,
            # not before the loop like in the original version.
            break

        #Mack edit: recalculate power each round from surviving individuals
        current_human_power = sum(health for h in humans)
        current_zombie_power = sum(z.health for z in zombies)

        if (
            current_human_power <= elimination_threshold
            or current_zombie_power <= elimination_threshold
        ):
            break

        battle = simulate_battle(
            human_power=current_human_power,
            zombie_power=current_zombie_power
        )

        losses = calculate_power_losses(
            human_power=current_human_power,
            zombie_power=current_zombie_power,
            result=battle["result"],
            base_loss_rate=base_loss_rate,
            margin_effect=margin_effect,
            wipeout_ratio=wipeout_ratio
        )

        #Mack change: spend the calculated losses on actual individuals ===
        humans = losses_to_population(humans, losses["human_power_lost"])
        zombies = losses_to_population(zombies, losses["zombie_power_lost"])

        battle_history.append({
            "battle_number": battle_number,
            "winner": battle["winner"],
            "result": battle["result"],
            "advantage": battle["advantage"],
            "uncertainty": battle["uncertainty"],
            "victory_margin": losses["victory_margin"],
            "starting_human_power": current_human_power,
            "starting_zombie_power": current_zombie_power,
            "human_power_lost": losses["human_power_lost"],
            "zombie_power_lost": losses["zombie_power_lost"],
            "humans_remaining": len(humans),
            "zombies_remaining": len(zombies)
        })
#Mack change: compares list lengths instead of floats
    if len(humans) > len(zombies):
        final_winner = "humans"
    elif len(zombies) > len(humans):
        final_winner = "zombies"
    else:
        final_winner = "draw"

    return {
        "winner": final_winner,
        "battles_fought": len(battle_history),
        "humans_remaining": len(humans),
        "zombies_remaining": len(zombies),
        "battle_history": battle_history
    }



#Mack edit: build the populations of individual objects

humans = create_population(Human, 50, "Human")
zombies = create_population(Zombie, 60, "Zombie")

conflict = simulate_conflict(
    humans=humans,
    zombies=zombies,
    number_of_battles=100
)

for battle in conflict["battle_history"]:
    print(
        f"Battle {battle['battle_number']}: "
        f"{battle['winner']} won | "
        f"Result: {battle['result']:.3f} | "
        f"Humans lost: {battle['human_power_lost']:.2f} | "
        f"Zombies lost: {battle['zombie_power_lost']:.2f} | "
        f"Remaining: H {battle['humans_remaining']}, Z {battle['zombies_remaining']}"
    )

print(f"Final winner: {conflict['winner']}")
print(f"Battles fought: {conflict['battles_fought']}")
print(f"Humans remaining: {conflict['humans_remaining']}")
print(f"Zombies remaining: {conflict['zombies_remaining']}")
