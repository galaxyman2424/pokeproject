"""
simulation/showdown_client.py

Low-level async websocket client for the local Pokémon Showdown server.
Handles the connection, login handshake, and raw message send/receive.
The battle agent and simulation runner sit on top of this.

Usage:
    client = ShowdownClient()
    await client.connect()
    await client.challenge_user("Bot2", "gen9ou", team_packed)
"""

import asyncio
import re
import websockets


SHOWDOWN_URL = "ws://localhost:8000/showdown/websocket"
BOT_USERNAME  = "PokeBot1"
BOT_PASSWORD  = ""          # empty — no-security mode


class ShowdownClient:
    def __init__(self, username: str = BOT_USERNAME):
        self.username   = username
        self.websocket  = None
        self.room_handlers = {}     # room_id -> async callable(room, lines)
        self._recv_task = None

    # ──────────────────────────────────────────────────────────────────────────
    # Connection
    # ──────────────────────────────────────────────────────────────────────────

    async def connect(self):
        """Open websocket and complete the login handshake."""
        self.websocket = await websockets.connect(SHOWDOWN_URL)
        print(f"[client] Connected to {SHOWDOWN_URL}")

        # Drain messages until we get challstr
        while True:
            raw = await self.websocket.recv()
            lines = self._parse_message(raw)
            got_challstr = any(tag == "challstr" for _, tag, _ in lines)
            if got_challstr:
                break

        # Send login and give server time to process it
        await self.send_global(f"/trn {self.username},0,")
        await asyncio.sleep(1.0)

        print(f"[client] Logged in as {self.username}")
        self._recv_task = asyncio.create_task(self._recv_loop())

    async def disconnect(self):
        if self._recv_task:
            self._recv_task.cancel()
        if self.websocket:
            await self.websocket.close()
        print("[client] Disconnected")

    # ──────────────────────────────────────────────────────────────────────────
    # Sending
    # ──────────────────────────────────────────────────────────────────────────

    async def send_global(self, message: str):
        """Send a global (lobby) command."""
        await self.websocket.send(message)

    async def send_room(self, room_id: str, message: str):
        """Send a message or command inside a battle room."""
        await self.websocket.send(f"{room_id}|{message}")

    async def send_move(self, room_id: str, move_slot: int):
        """Send a move choice (1-indexed slot)."""
        await self.send_room(room_id, f"/choose move {move_slot}")

    async def send_switch(self, room_id: str, slot: int):
        """Send a switch choice (1-indexed slot in party)."""
        await self.send_room(room_id, f"/choose switch {slot}")

    async def send_team(self, room_id: str, packed_team: str):
        """Send a packed team string to a room (used before battle start)."""
        await self.send_room(room_id, f"/team {packed_team}")

    # ──────────────────────────────────────────────────────────────────────────
    # Receiving
    # ──────────────────────────────────────────────────────────────────────────

    async def _recv_loop(self):
        """Background task — receive messages and dispatch to room handlers."""
        try:
            async for raw in self.websocket:
                print(f"[debug] RAW: {repr(raw[:200])}")
                lines = self._parse_message(raw)
                # Group lines by room
                by_room = {}
                for room, tag, rest in lines:
                    by_room.setdefault(room, []).append((tag, rest))

                for room, room_lines in by_room.items():
                    # Call specific room handler if registered
                    if room in self.room_handlers:
                        await self.room_handlers[room](room, room_lines)
                    # Always call wildcard handler ("*") for every room's messages
                    # Used by the runner to catch battle room init before registering
                    if "*" in self.room_handlers:
                        await self.room_handlers["*"](room, room_lines)
        except asyncio.CancelledError:
            pass
        except websockets.exceptions.ConnectionClosed:
            print("[client] Connection closed")
        

    def register_handler(self, room_id: str, handler):
        """Register an async handler for a specific battle room."""
        self.room_handlers[room_id] = handler

    def unregister_handler(self, room_id: str):
        self.room_handlers.pop(room_id, None)

    # ──────────────────────────────────────────────────────────────────────────
    # Challenging / accepting battles
    # ──────────────────────────────────────────────────────────────────────────

    async def challenge_user(self, opponent: str, format_id: str, packed_team: str):
        """Challenge another connected user to a battle."""
        await self.send_global(f"/utm {packed_team}")
        await self.send_global(f"/challenge {opponent}, {format_id}")
        print(f"[client] Challenged {opponent} to {format_id}")

    async def accept_challenge(self, opponent: str, packed_team: str):
        """Accept an incoming challenge from another user."""
        await self.send_global(f"/utm {packed_team}")
        await self.send_global(f"/accept {opponent}")
        print(f"[client] Accepted challenge from {opponent}")

    # ──────────────────────────────────────────────────────────────────────────
    # Message parsing
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_message(raw: str) -> list[tuple[str, str, str]]:
        """
        Parse a raw Showdown websocket message into a list of
        (room_id, tag, rest_of_line) tuples.

        Showdown messages look like:
            >battle-gen9ou-1234
            |init|battle
            |title|Bot1 vs Bot2
            |turn|1

        Global messages have no leading >room line, so room_id defaults to "".
        """
        lines_out = []
        current_room = ""
        for line in raw.split("\n"):
            if line.startswith(">"):
                current_room = line[1:].strip()
                continue
            if not line.startswith("|"):
                continue
            parts = line.split("|", 2)
            tag  = parts[1] if len(parts) > 1 else ""
            rest = parts[2] if len(parts) > 2 else ""
            lines_out.append((current_room, tag, rest))
        return lines_out


# ──────────────────────────────────────────────────────────────────────────────
# Packed team helpers
# ──────────────────────────────────────────────────────────────────────────────

def build_packed_team(sets: list[dict]) -> str:
    """
    Convert a list of set dicts into Showdown's packed team format string.

    Each set dict:
    {
        "name":     "Great Tusk",
        "species":  "Great Tusk",
        "item":     "Heavy-Duty Boots",
        "ability":  "Protosynthesis",
        "moves":    ["Headlong Rush", "Rapid Spin", "Ice Spinner", "Stealth Rock"],
        "nature":   "Jolly",
        "evs":      {"hp": 252, "atk": 4, "def": 0, "spa": 0, "spd": 0, "spe": 252},
        "ivs":      {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
        "level":    100,
        "tera_type": "Ground"
    }

    Packed format per Pokémon (pipe-separated fields):
        name|species|item|ability|moves(comma)|nature|evs|gender|ivs|shiny|level|happiness,gigantamax,dynamaxLevel,tera
    """
    packed_mons = []
    for s in sets:
        name     = s.get("name", s.get("species", ""))
        species  = s.get("species", "")
        item     = s.get("item", "")
        ability  = s.get("ability", "")
        moves    = ",".join(s.get("moves", []))
        nature   = s.get("nature", "Hardy")

        evs_dict = s.get("evs", {})
        evs = ",".join(str(evs_dict.get(k, 0)) for k in ["hp","atk","def","spa","spd","spe"])

        ivs_dict = s.get("ivs", {})
        ivs = ",".join(str(ivs_dict.get(k, 31)) for k in ["hp","atk","def","spa","spd","spe"])

        level     = s.get("level", 100)
        tera_type = s.get("tera_type", "")
        gender    = s.get("gender", "")
        shiny     = "S" if s.get("shiny", False) else ""

        # happiness,gigantamax,dynamaxLevel,tera_type packed into last field
        last = f",,{level},{tera_type}"

        packed = f"{name}|{species}|{item}|{ability}|{moves}|{nature}|{evs}|{gender}|{ivs}|{shiny}{last}"
        packed_mons.append(packed)

    return "]".join(packed_mons)


def parse_packed_team(packed: str) -> list[dict]:
    """Reverse of build_packed_team — parse a packed string back to set dicts."""
    sets = []
    for mon in packed.split("]"):
        parts = mon.split("|")
        if len(parts) < 12:
            continue
        evs_raw = parts[6].split(",")
        ivs_raw = parts[8].split(",")
        ev_keys = ["hp","atk","def","spa","spd","spe"]
        iv_keys = ["hp","atk","def","spa","spd","spe"]
        last    = parts[11] if len(parts) > 11 else ""
        last_parts = last.split(",")
        tera    = last_parts[3] if len(last_parts) > 3 else ""
        level   = int(last_parts[2]) if len(last_parts) > 2 and last_parts[2].isdigit() else 100

        sets.append({
            "name":      parts[0],
            "species":   parts[1] or parts[0],
            "item":      parts[2],
            "ability":   parts[3],
            "moves":     [m for m in parts[4].split(",") if m],
            "nature":    parts[5],
            "evs":       {k: int(v) if v.isdigit() else 0 for k, v in zip(ev_keys, evs_raw)},
            "ivs":       {k: int(v) if v.isdigit() else 31 for k, v in zip(iv_keys, ivs_raw)},
            "gender":    parts[7],
            "level":     level,
            "tera_type": tera,
        })
    return sets