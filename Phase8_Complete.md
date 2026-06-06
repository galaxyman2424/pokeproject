# Phase 8 — Visualization Dashboard: Complete (In Progress)

## Overview

Phase 8 builds a full-stack visualization dashboard on top of all previous phases. A FastAPI backend exposes the project's analytical outputs as a REST API, and a React + TailwindCSS frontend consumes it to deliver an interactive competitive Pokémon analytics platform. The dashboard covers metagame analysis, team building with live recommendations, and optimizer result inspection.

---

## Environment

| Property | Value |
| :--- | :--- |
| Operating System | Linux Mint |
| IDE | VSCode |
| Project Location | `~/pokeproject` |
| Python Version | Python 3.12 |
| Virtual Environment | `~/pokeproject/venv` |
| Node.js Version | v20.x (upgraded from v18 via nvm) |
| Backend Port | 8001 (FastAPI + uvicorn) |
| Frontend Port | 5173 (Vite dev server) |

**New Python dependencies installed:**
```
fastapi
uvicorn
```

**New Node dependencies installed:**
```
axios
recharts
tailwindcss@3
postcss
autoprefixer
```

---

## Project File Structure

```
~/pokeproject/
├── api/
│   ├── __init__.py
│   └── main.py               # FastAPI app — all REST endpoints
├── dashboard/                # Vite + React frontend
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.jsx
│       ├── index.css
│       ├── App.jsx           # Tab navigation shell
│       ├── api.js            # All axios calls in one place
│       └── pages/
│           ├── Metagame.jsx  # Usage stats, pairs, tera, triplets
│           ├── TeamBuilder.jsx # Team input, threat analysis, recommendations
│           └── Optimizer.jsx  # Phase 5 results, generation history chart
└── ...
```

---

## Running the Dashboard

Both servers must be running simultaneously in separate terminals.

**Terminal 1 — Backend:**
```bash
cd ~/pokeproject
source venv/bin/activate
python -m uvicorn api.main:app --port 8001 --reload
```

**Terminal 2 — Frontend:**
```bash
cd ~/pokeproject/dashboard
npm run dev
```

Open `http://localhost:5173` in the browser.

---

## Backend — FastAPI

The API is defined in `api/main.py` and exposes the following endpoints:

### Metagame
| Endpoint | Description |
| :--- | :--- |
| `GET /meta/usage` | Pokémon usage %, win rates, appearance counts |
| `GET /meta/pairs` | Co-occurring Pokémon pairs with win rates |
| `GET /meta/triplets` | Top triplet cores |
| `GET /meta/tera` | Terastallization rates per Pokémon |
| `GET /meta/tera/{pokemon}` | Tera type distribution for a specific species |
| `GET /meta/moves/{pokemon}` | Move frequency distribution for a specific species |

### Team Analysis
| Endpoint | Description |
| :--- | :--- |
| `GET /team/analyze` | Full Phase 4 threat report for a given team |
| `GET /team/recommend` | Phase 7 recommendations for a partial team |

### Optimizer
| Endpoint | Description |
| :--- | :--- |
| `GET /optimizer/results` | Full Phase 5 generation history JSON |
| `GET /optimizer/best` | Top N unique teams across all generations |

### Pokédex
| Endpoint | Description |
| :--- | :--- |
| `GET /pokemon/{name}` | Types, base stats, abilities for a species |
| `GET /pokemon/{name}/weaknesses` | Full type effectiveness breakdown |

Interactive API docs available at `http://localhost:8001/docs`.

---

## Frontend — React

Three pages accessible via tab navigation:

### Metagame
- Horizontal bar chart of top 20 Pokémon by usage %
- Usage and win rate table with color-coded win rates (green ≥55%, red ≤45%)
- Top co-occurring pairs table with win rates
- Terastallization rate bar chart
- Top triplet cores table

### Team Builder
- Pokémon name input with Enter key support
- Live team slot display (up to 6) with remove buttons
- Analyze button triggers Phase 4 threat analysis + Phase 7 recommendations simultaneously
- Threat score display (0–100, color-coded green/yellow/red)
- Type holes visualization with exposure bars
- Speed tier panel (max/avg/min) with outsped-by list
- Role coverage gaps list
- Archetype weakness flags (Rain, Sun, HO)
- Meta coverage score
- Recommendation table with score breakdown and one-click Add to team

### Optimizer
- Line chart of best and average fitness score per generation
- Top 10 unique optimized teams with fitness scores and per-component score breakdowns
- Graceful empty state when Phase 5 hasn't been run

---

## Known Issues and Limitations

- Item data from Phase 2 is sparse by nature (only observed activations) and is not currently visualized in the dashboard
- The Optimizer page expects a specific JSON structure from `output/optimizer_results.json` — if Phase 5 was run with custom flags the generation history parsing may need adjustment
- No authentication or rate limiting on the API — intended for local development use only

---

## Next Steps

The following features are planned for continued Phase 8 development:

### 1 — Pokémon Sprites
Pull sprite images from the PokeAPI (`https://pokeapi.co/api/v2/pokemon/{name}`) and display them throughout the UI — next to names in the usage table, in the team builder slots, and alongside recommendation results. Falls back to a placeholder silhouette for unknown species.

### 2 — Move Detail Panel
Clicking a Pokémon name anywhere in the dashboard opens a slide-out panel showing:
- Full move frequency distribution from Phase 2 (bar chart)
- Tera type distribution (pie or bar chart)
- Base stats radar chart
- Item usage breakdown
- Type badges and weaknesses

### 3 — Matchup Heatmap
A D3-powered 6×18 heatmap in the Team Builder showing type effectiveness across all 6 team members against all 18 attacking types. Cells colored by multiplier (red = 2x weak, green = 0.5x resist, black = immune). Gives an at-a-glance view of the team's defensive profile without reading the threat report.

### 4 — Live Optimizer Run
A new UI panel that triggers a Phase 5 genetic algorithm run directly from the browser. The backend streams generation results via a Server-Sent Events (SSE) endpoint as the optimizer runs. The frontend updates the score chart in real time and displays the current best team as it evolves. Includes configurable parameters (generations, population size, battles per matchup).

### 5 — Showdown Paste Export
A button in the Team Builder that converts the current team to a Pokémon Showdown importable paste format using the Phase 6 `complete_set` and `build_packed_team` logic exposed via a new `/team/export` endpoint. Copies to clipboard with one click. Allows teams built in the dashboard to be immediately used in actual Showdown battles.

### 6 — Metagame Search and Filter
Add filtering controls to the Metagame usage table:
- Filter by type (show only Fire-types, etc.)
- Filter by usage range (slider)
- Filter by win rate threshold
- Sort by any column
- Search by name

Also add a date/batch selector if multiple pipeline runs are stored, enabling metagame trend comparison over time.

---

## Phase 8 Deliverable (Current State)

A working full-stack dashboard that:

- Serves all Phase 2–7 analytical outputs via a clean REST API
- Visualizes metagame usage, co-occurrence, and tera data with interactive charts
- Provides a live team building interface with integrated threat analysis and recommendations
- Displays Phase 5 optimizer results with generation history visualization
- Runs entirely locally with no external dependencies beyond the existing project stack
