# Used to pull data from your SQL Posgres database
# You can also edit values via functions in here
# Currently lacks a fluent way of use (must type out functions manually atm)

import psycopg

from dataclasses import dataclass
from psycopg.rows import class_row


# ============================================================
# Agent classes
# ============================================================

@dataclass
class Agent:
    agent_id: int
    is_alive: bool
    health: int
    speed: int


@dataclass
class Human(Agent):
    weapon_tier: int
    x_pos: int
    y_pos: int


@dataclass
class Zombie(Agent):
    strength: int
    x_pos: int
    y_pos: int


# ============================================================
# Database repository
# ============================================================

class AgentRepository:
    def __init__(
        self,
        dbname: str,
        user: str,
        password: str,
        host: str = "localhost",
        port: int = 5432
    ):
        self.connection_info = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port
        }

        self.conn = None

    # --------------------------------------------------------
    # Connection management
    # --------------------------------------------------------

    def __enter__(self):
        self.conn = psycopg.connect(**self.connection_info)
        return self

    def __exit__(
        self,
        exception_type,
        exception_value,
        traceback
    ):
        if self.conn is None:
            return

        try:
            if exception_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.conn.close()
            self.conn = None

    def _check_connection(self) -> None:
        if self.conn is None or self.conn.closed:
            raise RuntimeError(
                "The database connection is not open. "
                "Use AgentRepository inside a with statement."
            )

    # ========================================================
    # Human queries
    # ========================================================

    def get_all_humans(self) -> list[Human]:
        self._check_connection()
        query = """
            SELECT
                a.agent_id AS agent_id,
                a.is_alive,
                a.health,
                a.speed,
                h.weapon_tier,
                h.x_pos,
                h.y_pos
            FROM agents AS a
            INNER JOIN humans AS h
                ON h.agent_id = a.agent_id
            ORDER BY a.agent_id;
        """

        with self.conn.cursor(
            row_factory=class_row(Human)
        ) as cur:
            cur.execute(query)
            return cur.fetchall()

    def get_human(self, agent_id: int) -> Human | None:
        self._check_connection()

        query = """
            SELECT
                a.agent_id AS agent_id,
                a.is_alive,
                a.health,
                a.speed,
                h.weapon_tier,
                h.x_pos,
                h.y_pos
            FROM agents AS a
            INNER JOIN humans AS h
                ON h.agent_id = a.agent_id
            WHERE a.agent_id = %s;
        """

        with self.conn.cursor(
            row_factory=class_row(Human)
        ) as cur:
            cur.execute(query, (agent_id,))
            return cur.fetchone()

    # ========================================================
    # Zombie queries
    # ========================================================

    def get_all_zombies(self) -> list[Zombie]:
        self._check_connection()

        query = """
            SELECT
                a.agent_id AS agent_id,
                a.is_alive,
                a.health,
                a.speed,
                z.strength,
                z.x_pos,
                z.y_pos
            FROM agents AS a
            INNER JOIN zombies AS z
                ON z.agent_id = a.agent_id
            ORDER BY a.agent_id;
        """

        with self.conn.cursor(
            row_factory=class_row(Zombie)
        ) as cur:
            cur.execute(query)
            return cur.fetchall()

    def get_zombie(self, agent_id: int) -> Zombie | None:
        self._check_connection()

        query = """
            SELECT
                a.agent_id AS agent_id,
                a.is_alive,
                a.health,
                a.speed,
                z.strength,
                z.x_pos,
                z.y_pos
            FROM agents AS a
            INNER JOIN zombies AS z
                ON z.agent_id = a.agent_id
            WHERE a.agent_id = %s;
        """

        with self.conn.cursor(
            row_factory=class_row(Zombie)
        ) as cur:
            cur.execute(query, (agent_id,))
            return cur.fetchone()

    # ========================================================
    # General agent updates
    # ========================================================

    def update_health(
        self,
        agent_id: int,
        new_health: int
    ) -> None:
        self._check_connection()

        # Prevent health from going below zero.
        new_health = max(0, new_health)
        is_alive = new_health > 0

        query = """
            UPDATE agents
            SET
                health = %s,
                is_alive = %s
            WHERE agent_id = %s;
        """

        with self.conn.cursor() as cur:
            cur.execute(
                query,
                (new_health, is_alive, agent_id)
            )

            if cur.rowcount == 0:
                raise ValueError(
                    f"Agent with ID {agent_id} was not found."
                )

    def update_speed(
        self,
        agent_id: int,
        new_speed: int
    ) -> None:
        self._check_connection()

        query = """
            UPDATE agents
            SET speed = %s
            WHERE agent_id = %s;
        """

        with self.conn.cursor() as cur:
            cur.execute(
                query,
                (new_speed, agent_id)
            )

            if cur.rowcount == 0:
                raise ValueError(
                    f"Agent with ID {agent_id} was not found."
                )

    # ========================================================
    # Human updates
    # ========================================================

    def update_human_position(
        self,
        agent_id: int,
        x_pos: int,
        y_pos: int
    ) -> None:
        self._check_connection()

        query = """
            UPDATE humans
            SET
                x_pos = %s,
                y_pos = %s
            WHERE agent_id = %s;
        """

        with self.conn.cursor() as cur:
            cur.execute(
                query,
                (x_pos, y_pos, agent_id)
            )

            if cur.rowcount == 0:
                raise ValueError(
                    f"Human with ID {agent_id} was not found."
                )

    def update_weapon_tier(
        self,
        agent_id: int,
        new_weapon_tier: int
    ) -> None:
        self._check_connection()

        query = """
            UPDATE humans
            SET weapon_tier = %s
            WHERE agent_id = %s;
        """

        with self.conn.cursor() as cur:
            cur.execute(
                query,
                (new_weapon_tier, agent_id)
            )

            if cur.rowcount == 0:
                raise ValueError(
                    f"Human with ID {agent_id} was not found."
                )

    # ========================================================
    # Zombie updates
    # ========================================================

    def update_zombie_position(
        self,
        agent_id: int,
        x_pos: int,
        y_pos: int
    ) -> None:
        self._check_connection()

        query = """
            UPDATE zombies
            SET
                x_pos = %s,
                y_pos = %s
            WHERE agent_id = %s;
        """

        with self.conn.cursor() as cur:
            cur.execute(
                query,
                (x_pos, y_pos, agent_id)
            )

            if cur.rowcount == 0:
                raise ValueError(
                    f"Zombie with ID {agent_id} was not found."
                )

    def update_zombie_strength(
        self,
        agent_id: int,
        new_strength: int
    ) -> None:
        self._check_connection()

        query = """
            UPDATE zombies
            SET strength = %s
            WHERE agent_id = %s;
        """

        with self.conn.cursor() as cur:
            cur.execute(
                query,
                (new_strength, agent_id)
            )

            if cur.rowcount == 0:
                raise ValueError(
                    f"Zombie with ID {agent_id} was not found."
                )


def main():
    with AgentRepository(
        dbname="zombie_game",
        user="postgres",
        password="0731",
        host="localhost",
        port=5432
    ) as repository:

        humans = repository.get_all_humans()
        zombies = repository.get_all_zombies()

        print("Humans")

        for human in humans:
            print(
                f"Human {human.agent_id}: "
                f"alive={human.is_alive}, "
                f"health={human.health}, "
                f"speed={human.speed}, "
                f"weapon tier={human.weapon_tier}, "
                f"position=({human.x_pos}, {human.y_pos})"
            )

        print("\nZombies")

        for zombie in zombies:
            print(
                f"Zombie {zombie.agent_id}: "
                f"alive={zombie.is_alive}, "
                f"health={zombie.health}, "
                f"speed={zombie.speed}, "
                f"strength={zombie.strength}, "
                f"position=({zombie.x_pos}, {zombie.y_pos})"
            )
        # I want to update human 32's weapon tier to 5 and position to (10, 20)
        human = repository.get_human(32)
        if human:
            repository.update_weapon_tier(human.agent_id, 5)
            repository.update_human_position(human.agent_id, 10, 20)
            print(
                f"\nUpdated Human {human.agent_id}: weapon tier set to 5 and position set to (10, 20)")
        else:
            print("\nHuman with ID 32 not found.")


if __name__ == "__main__":
    main()
