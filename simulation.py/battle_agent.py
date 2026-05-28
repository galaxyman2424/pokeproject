"""
simulation/battle_agent.py

Greedy damage-maximizing battle agent.

Each turn the agent:
1. Looks at the opposing active Pokémon's types
2. Scores each available move by expected type effectiveness
3. Picks the highest-scoring move
4. Falls back to a switch if all moves are blocked (Choice lock, etc.)

The agent tracks battle state from the Showdown message stream so it always
knows which Pokémon are active, which are fainted, and which moves are available.

Usage:
    agent = BattleAgent(pid="p1", team_sets=[...])
    choice = agent.choose(available_moves, available_switches, opponent_active_types)
    # returns ("move", slot) or ("switch", slot)
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from analysis.pokemon_data import get_types, get_type_effectiveness, ALL_TYPES


# Move categories — used to score non-damaging moves
STATUS_MOVES = {
    "Stealth Rock", "Spikes", "Toxic Spikes", "Sticky Web",
    "Rapid Spin", "Defog", "Recover", "Roost", "Soft-Boiled",
    "Wish", "Protect", "Substitute", "Will-O-Wisp", "Thunder Wave",
    "Toxic", "Swords Dance", "Nasty Plot", "Dragon Dance", "Calm Mind",
    "Quiver Dance", "Trick Room", "Tailwind", "Light Screen", "Reflect",
    "Aurora Veil", "Knock Off", "U-turn", "Volt Switch", "Flip Turn",
    "Parting Shot", "Trick", "Encore", "Taunt",
}

# Pivot moves — we score these moderately so the agent uses them situationally
PIVOT_MOVES = {"U-turn", "Volt Switch", "Flip Turn", "Parting Shot"}

# Priority moves — slight score boost
PRIORITY_MOVES = {
    "Extreme Speed", "Sucker Punch", "Bullet Punch",
    "Aqua Jet", "Shadow Sneak", "Ice Shard", "Quick Attack",
    "Mach Punch", "Vacuum Wave", "Water Shuriken",
}

# Move type lookup — hardcoded for common competitive moves
# For moves not in this table, type defaults to "Normal"
MOVE_TYPE = {
    # Normal
    "Headlong Rush": "Ground", "Rapid Spin": "Normal", "Ice Spinner": "Ice",
    "Stealth Rock": "Rock", "Earthquake": "Ground", "Close Combat": "Fighting",
    "Extreme Speed": "Normal", "Hyper Voice": "Normal", "Boomburst": "Normal",
    "Body Press": "Fighting", "Facade": "Normal", "Return": "Normal",
    "Double-Edge": "Normal", "Tackle": "Normal",
    # Fire
    "Flamethrower": "Fire", "Fire Blast": "Fire", "Heat Wave": "Fire",
    "Sacred Fire": "Fire", "Overheat": "Fire", "Flare Blitz": "Fire",
    "Weather Ball": "Fire",   # changes with weather — default Fire for sun
    # Water
    "Surf": "Water", "Hydro Pump": "Water", "Scald": "Water",
    "Aqua Jet": "Water", "Flip Turn": "Water", "Liquidation": "Water",
    "Steam Eruption": "Water", "Chilling Water": "Water",
    # Grass
    "Giga Drain": "Grass", "Leaf Storm": "Grass", "Power Whip": "Grass",
    "Wood Hammer": "Grass", "Energy Ball": "Grass",
    # Electric
    "Thunderbolt": "Electric", "Thunder": "Electric", "Volt Switch": "Electric",
    "Wild Charge": "Electric", "Discharge": "Electric", "Parabolic Charge": "Electric",
    # Ice
    "Ice Beam": "Ice", "Blizzard": "Ice", "Ice Shard": "Ice",
    "Freeze-Dry": "Ice", "Triple Axel": "Ice", "Glacial Lance": "Ice",
    # Fighting
    "Mach Punch": "Fighting", "Vacuum Wave": "Fighting",
    "Aura Sphere": "Fighting", "Focus Blast": "Fighting",
    "Superpower": "Fighting", "High Jump Kick": "Fighting",
    "Cross Chop": "Fighting", "Low Kick": "Fighting",
    # Poison
    "Sludge Bomb": "Poison", "Sludge Wave": "Poison", "Gunk Shot": "Poison",
    "Poison Jab": "Poison",
    # Ground
    "Earth Power": "Ground", "Drill Run": "Ground", "Stomping Tantrum": "Ground",
    "High Horsepower": "Ground",
    # Flying
    "Brave Bird": "Flying", "Air Slash": "Flying", "Hurricane": "Flying",
    "Acrobatics": "Flying", "Dual Wingbeat": "Flying",
    # Psychic
    "Psychic": "Psychic", "Psyshock": "Psychic", "Expanding Force": "Psychic",
    "Future Sight": "Psychic", "Stored Power": "Psychic",
    # Bug
    "U-turn": "Bug", "Bug Buzz": "Bug", "X-Scissor": "Bug",
    "First Impression": "Bug",
    # Rock
    "Rock Slide": "Rock", "Stone Edge": "Rock", "Power Gem": "Rock",
    "Head Smash": "Rock",
    # Ghost
    "Shadow Ball": "Ghost", "Shadow Sneak": "Ghost", "Hex": "Ghost",
    "Phantom Force": "Ghost", "Astral Barrage": "Ghost",
    # Dragon
    "Dragon Claw": "Dragon", "Draco Meteor": "Dragon", "Outrage": "Dragon",
    "Dragon Darts": "Dragon", "Dragon Pulse": "Dragon", "Scale Shot": "Dragon",
    "Roaring Moon": "Dragon",
    # Dark
    "Knock Off": "Dark", "Sucker Punch": "Dark", "Crunch": "Dark",
    "Foul Play": "Dark", "Kowtow Cleave": "Dark", "Dark Pulse": "Dark",
    "Night Slash": "Dark",
    # Steel
    "Iron Head": "Steel", "Flash Cannon": "Steel", "Make It Rain": "Steel",
    "Bullet Punch": "Steel", "Gyro Ball": "Steel", "Iron Defense": "Steel",
    "Steel Beam": "Steel",
    # Fairy
    "Moonblast": "Fairy", "Dazzling Gleam": "Fairy", "Play Rough": "Fairy",
    "Mystical Fire": "Fairy", "Spirit Break": "Fairy",
    # Special Gholdengo / Dragapult
    "Nasty Plot": "Normal",  # status
    "Recover": "Normal",     # status
    "Roost": "Flying",       # status
    "Swords Dance": "Normal","Dragon Dance": "Normal","Calm Mind": "Normal",
    "Quiver Dance": "Normal","Trick": "Psychic","Will-O-Wisp": "Fire",
    "Thunder Wave": "Electric","Toxic": "Poison","Taunt": "Dark",
    "Protect": "Normal", "Substitute": "Normal",
    # Additional OU moves
    "Spore": "Grass", "Leech Seed": "Grass",
    "Eruption": "Fire", "Water Spout": "Water",
    "Lava Plume": "Fire", "Magma Storm": "Fire",
    "Precipice Blades": "Ground", "Thousand Arrows": "Ground",
    "Thousand Waves": "Ground", "Lands Wrath": "Ground",
    "Diamond Storm": "Rock", "Moongeist Beam": "Ghost",
    "Sunsteel Strike": "Steel", "Searing Sunraze Smash": "Steel",
    "Menacing Moonraze Maelstrom": "Ghost",
    "Ice Burn": "Ice", "Freeze Shock": "Ice",
    "V-create": "Fire", "Blue Flare": "Fire",
    "Bolt Strike": "Electric", "Fusion Flare": "Fire", "Fusion Bolt": "Electric",
    "Glaciate": "Ice", "Tail Glow": "Bug",
    "Shell Smash": "Normal", "Shift Gear": "Steel",
    "Geomancy": "Fairy", "Sticky Web": "Bug",
    "Defog": "Flying", "Haze": "Ice", "Perish Song": "Normal",
    "Encore": "Normal", "Trick Room": "Psychic",
    "Tailwind": "Flying", "Light Screen": "Psychic", "Reflect": "Psychic",
    "Aurora Veil": "Ice", "Parting Shot": "Dark",
    "Spikes": "Ground", "Toxic Spikes": "Poison",
}


def get_move_type(move_name: str) -> str:
    return MOVE_TYPE.get(move_name, "Normal")


def score_move(move_name: str, opponent_types: list[str]) -> float:
    """
    Score a move against the opponent's active Pokémon types.
    Returns expected damage multiplier (higher = better).
    Status moves score 0.5 — use them only as a last resort.
    Pivot moves score 0.8 — use them if nothing is strong.
    """
    if move_name in STATUS_MOVES and move_name not in PIVOT_MOVES:
        return 0.5
    if move_name in PIVOT_MOVES:
        return 0.8

    move_type = get_move_type(move_name)
    effectiveness = get_type_effectiveness(move_type, opponent_types)

    # Small boost for priority
    if move_name in PRIORITY_MOVES:
        effectiveness *= 1.1

    return effectiveness


class BattleAgent:
    """
    Stateful battle agent for one side of a simulated battle.

    The agent tracks:
    - Which Pokémon are in the party and their HP status (alive/fainted)
    - Which Pokémon is currently active
    - Available moves and switches each turn (as reported by Showdown's |request| message)

    On each turn, it picks the highest-scoring legal move.
    """

    def __init__(self, pid: str, team_sets: list[dict]):
        """
        pid:       "p1" or "p2"
        team_sets: list of complete set dicts (from set_completion.py)
        """
        self.pid       = pid
        self.team_sets = team_sets
        self.party     = {s["name"]: {"hp": 1.0, "fainted": False} for s in team_sets}
        self.active    = None   # name of currently active Pokémon

    # ──────────────────────────────────────────────────────────────────────────
    # State updates from battle messages
    # ──────────────────────────────────────────────────────────────────────────

    def handle_switch(self, pokemon_name: str):
        """Call when this agent's Pokémon switches in."""
        self.active = pokemon_name

    def handle_faint(self, pokemon_name: str):
        """Call when a Pokémon faints."""
        if pokemon_name in self.party:
            self.party[pokemon_name]["fainted"] = True
        if self.active == pokemon_name:
            self.active = None

    def handle_damage(self, pokemon_name: str, hp_fraction: float):
        """Call when a Pokémon takes damage. hp_fraction is 0.0–1.0."""
        if pokemon_name in self.party:
            self.party[pokemon_name]["hp"] = hp_fraction

    def living_party(self) -> list[str]:
        """Returns names of non-fainted Pokémon."""
        return [n for n, s in self.party.items() if not s["fainted"]]

    def bench(self) -> list[str]:
        """Returns non-active, non-fainted Pokémon (valid switch targets)."""
        return [n for n in self.living_party() if n != self.active]

    # ──────────────────────────────────────────────────────────────────────────
    # Decision making
    # ──────────────────────────────────────────────────────────────────────────

    def choose_move(
        self,
        available_moves: list[str],
        opponent_active_types: list[str],
    ) -> tuple[str, int]:
        """
        Choose the best move against the opponent's active Pokémon.

        Args:
            available_moves:       List of move names (up to 4), in slot order
            opponent_active_types: Type list of the opponent's active Pokémon

        Returns:
            ("move", 1-indexed slot) or ("switch", 1-indexed bench slot)
        """
        if not available_moves:
            return self._choose_switch()

        scored = []
        for i, move in enumerate(available_moves, start=1):
            score = score_move(move, opponent_active_types)
            scored.append((score, i, move))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_slot, best_move = scored[0]

        # If best option is a status move or pivot, prefer switching if possible
        if best_score <= 0.8 and self.bench():
            return self._choose_switch()

        return ("move", best_slot)

    def _choose_switch(self) -> tuple[str, int]:
        """
        Choose a switch target when no good move is available.
        Picks the first available bench Pokémon.
        """
        bench = self.bench()
        if not bench:
            # No valid switch — this shouldn't happen in a legal battle state
            return ("move", 1)

        living = self.living_party()
        # 1-indexed slot in the full party order (not just bench)
        for i, name in enumerate(living, start=1):
            if name != self.active:
                return ("switch", i)

        return ("move", 1)

    def forced_switch(self) -> tuple[str, int]:
        """
        Called when the active Pokémon has fainted and a switch is mandatory.
        Picks the bench member with the best type coverage against unknown opponent.
        """
        bench = self.bench()
        if not bench:
            return ("switch", 1)

        living = self.living_party()
        for i, name in enumerate(living, start=1):
            if name in bench:
                return ("switch", i)

        return ("switch", 1)