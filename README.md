<div align="center">

<img src="assets/forreadme/logo2.png" alt="UrbanFlow AI banner" width="100%"/>

<br/>

<img src="assets/forreadme/logo.png" alt="UrbanFlow AI logo" width="300"/>

# UrbanFlow AI

[![Русский](https://img.shields.io/badge/README_Language-Русский-blue)](https://github.com/TheAndreyZakharov/UrbanFlow-AI/blob/main/README_RU.md)
[![English](https://img.shields.io/badge/README_Language-English-brightgreen)](https://github.com/TheAndreyZakharov/UrbanFlow-AI/blob/main/README.md)

</div>

UrbanFlow AI is a web application for 3D traffic simulation on real OpenStreetMap areas.

The project imports real OSM data, builds a browser-based 3D city scene, generates a SUMO traffic scenario, runs microscopic traffic simulation for vehicles, pedestrians, buses, trams and other public transport, and allows an AI controller to manage real SUMO traffic lights through TraCI.

The main goal is to test how a real urban road network behaves under different traffic loads, road events and traffic-light control strategies.

UrbanFlow AI combines:

- OpenStreetMap area selection;
- OSM-based 3D city generation;
- SUMO microscopic traffic simulation;
- TraCI runtime control;
- dynamic vehicle spawning;
- SUMO pedestrians;
- public transport routes and stops;
- road-event editor;
- traffic-light override tools;
- UrbanFlow AI traffic-light controller;
- visual AI training;
- saved model registry;
- live metrics;
- generated Jupyter notebooks and training analytics.

This project is a technical, educational and research-oriented prototype for traffic simulation, urban planning workflows, AI traffic-light control and SUMO integration.

## Core concept

UrbanFlow AI is not a decorative traffic animation.

The 3D scene is a visualization layer over a real SUMO simulation. Vehicles, pedestrians and public transport are controlled by SUMO. Traffic lights are real SUMO traffic lights. When the simulation uses SUMO automatic mode, SUMO controls the signals. When the simulation uses UrbanFlow AI mode, the AI controller changes SUMO traffic-light phases through TraCI, and SUMO-controlled vehicles still obey those lights.

The frontend renders the state coming from the backend. The backend owns the SUMO session, OSM import, scenario generation, editor patches, training jobs and AI controller state.

## How it works

Processing flow:

    User selects an OSM area
              ↓
    Frontend sends the bounding box to the backend
              ↓
    Backend imports and normalizes OpenStreetMap data
              ↓
    Backend builds a SUMO scenario
              ↓
    SUMO starts a microscopic traffic simulation
              ↓
    Vehicles, pedestrians and public transport move in SUMO
              ↓
    React/Three.js frontend renders the 3D city and actors
              ↓
    SUMO, fixed logic or UrbanFlow AI controls traffic lights
              ↓
    Metrics, training artifacts and notebooks are generated

UrbanFlow AI uses OpenStreetMap data quality as the source of the generated city. Different cities and districts may have different levels of detail depending on how completely they are mapped by the OSM community.

## Technology stack

Frontend:

- React;
- Vite;
- TypeScript;
- React Leaflet;
- Three.js / React Three Fiber style 3D scene architecture;
- browser-based UI panels for simulation, editor, training and metrics.

Backend:

- FastAPI;
- Python;
- SUMO;
- TraCI;
- OSM import and normalization;
- SUMO scenario generation;
- runtime simulation session store;
- AI training job store;
- JSON checkpoint model registry.

AI and analytics:

- UrbanFlow AI runtime controller;
- JSON checkpoint policy;
- reward calculation from SUMO metrics;
- visual training loop;
- generated `training_history.csv`;
- generated `training_history.jsonl`;
- generated model checkpoints;
- generated Jupyter notebooks with embedded charts and tables.

## Current AI model format

The current runtime model is a JSON checkpoint policy.

It is not currently a PyTorch neural network, ONNX model or TorchScript model.

The active runtime artifact is:

    JSON checkpoint policy

ONNX and TorchScript export are intentionally hidden until a real neural policy is connected.

## First screen

On first launch, the application opens with an empty 3D workspace and navigation controls.

<div align="center">

<img src="assets/forreadme/1.png" alt="UrbanFlow AI first launch screen" width="600"/>

</div>

The central area is reserved for the 3D city scene. Before an area is generated, the user is prompted to open the map and select a real OSM area.

## Metrics and AI drawer

The right-side drawer contains simulation metrics, AI status, live charts and the model registry.

<div align="center">

<img src="assets/forreadme/2.png" alt="UrbanFlow AI metrics and AI drawer" width="600"/>

</div>

This panel is used to inspect:

- active vehicles;
- active pedestrians;
- average speed;
- average waiting time;
- congestion score;
- stopped vehicles;
- AI reward;
- training status;
- saved models;
- live metric charts.

## Map selector

The first left-side control opens the OpenStreetMap selector.

<div align="center">

<img src="assets/forreadme/3.png" alt="UrbanFlow AI OpenStreetMap selector overview" width="600"/>

</div>

The map starts from a wide world-level view.

The bottom control bar contains:

- search field for a city, street or district;
- area side length in meters;
- `+` and `-` buttons for changing the area size by 100 meters;
- search action;
- selected-area confirmation action.

After the user confirms the selected area, the backend starts importing OSM data and generating the SUMO scenario.

## Searching and selecting an area

After entering a place name, the map focuses on the found location and zooms in for area selection.

<div align="center">

<img src="assets/forreadme/4.jpeg" alt="UrbanFlow AI selected OSM area after search" width="600"/>

</div>

The green square shows the selected simulation area. It defines the bounding box sent to the backend.

The selected area size can be changed before generation. Larger areas can contain more roads, buildings and intersections, but also require more processing time and more simulation resources.

## Area generation screen

During OSM import and scenario generation, the application shows a loading screen.

<div align="center">

<img src="assets/forreadme/5.jpeg" alt="UrbanFlow AI area generation loading screen" width="600"/>

</div>

At this stage, the backend can perform several operations:

- OSM data import;
- OSM normalization;
- SUMO network generation;
- route and trip generation;
- pedestrian trip generation;
- public transport artifact generation;
- traffic-light repair and validation;
- simulation session creation.

## Generated 3D city scene

After generation, the selected area appears as a 3D city scene.

<div align="center">

<img src="assets/forreadme/6.jpeg" alt="UrbanFlow AI generated 3D city scene" width="600"/>

</div>

The scene can be navigated with keyboard and mouse controls.

Controls:

- `W` — move forward;
- `S` — move backward;
- `A` — move left;
- `D` — move right;
- left mouse button — rotate the camera;
- right mouse button — drag/pan the view.

The scene renders the generated city, roads, traffic actors, events and optional visual layers.

## Simulation controls

The Simulation panel configures the active SUMO simulation.

<div align="center">

<img src="assets/forreadme/7.jpeg" alt="UrbanFlow AI simulation controls panel" width="600"/>

</div>

Available controls include:

- play and pause;
- reset;
- simulation speed;
- vehicle count;
- pedestrian count;
- traffic-light mode;
- traffic-light override;
- OSM-only signals or all possible intersections;
- apply counts and signals.

Traffic-light control modes:

- `SUMO automatic control` — SUMO controls traffic-light programs;
- `Manual fixed cycle` — simple fixed-cycle logic;
- `UrbanFlow AI control` — UrbanFlow AI loads the latest saved JSON checkpoint model and controls SUMO traffic lights through TraCI.

Traffic-light override can force all controlled lights to one color for testing. Vehicles are still controlled by SUMO and respond to the resulting signal states.

## Bridges, tunnels, stops and signal visibility

The 3D scene supports different road levels and transport-related map elements.

<div align="center">

<img src="assets/forreadme/8.png" alt="UrbanFlow AI bridges tunnels stops and disabled full signal display" width="600"/>

</div>

The scene can display:

- bridges;
- multi-level interchanges;
- tunnels;
- stops;
- public transport infrastructure;
- traffic lights;
- traffic-light color indicators.

Traffic-light colors are also projected onto the small base/platform under the signal to make the state more readable from the camera.

## All intersections and forced signal state

The simulation can be rebuilt or configured with signals on all possible intersections.

<div align="center">

<img src="assets/forreadme/9.jpeg" alt="UrbanFlow AI all possible traffic lights with forced green override" width="600"/>

</div>

This mode is useful for testing AI control on a much larger set of intersections.

To apply changed vehicle counts or traffic-light scope, use the `Apply counts and signals` action in the Simulation panel.

## Road editor

The Editor panel allows the user to apply road events and road-access changes.

<div align="center">

<img src="assets/forreadme/10.png" alt="UrbanFlow AI road editor panel" width="600"/>

</div>

Supported runtime editor actions include:

- close road;
- open road;
- roadwork;
- accident point;
- automated random road events.

Current runtime behavior:

- closed roads disallow vehicle movement through the selected SUMO edges;
- opened roads restore access;
- roadwork reduces allowed speed on the affected road;
- accident points slow vehicles within a local radius around the selected point;
- automated events can be configured by duration and frequency.

## Closing a road

The user can select a road and mark it as closed.

<div align="center">

<img src="assets/forreadme/11.jpeg" alt="UrbanFlow AI selecting a road to close" width="600"/>

</div>

A closed road becomes unavailable for vehicle traffic. SUMO vehicles do not use it as a normal drivable road.

## Opening a road

The editor can also explicitly open a selected road.

<div align="center">

<img src="assets/forreadme/12.jpeg" alt="UrbanFlow AI selecting a road to open" width="600"/>

</div>

This is useful when a road was previously closed by a manual event or an automated scenario.

## Roadwork

Roadwork applies a lower speed limit to the selected road.

<div align="center">

<img src="assets/forreadme/13.jpeg" alt="UrbanFlow AI selecting a roadwork location" width="600"/>

</div>

In the current implementation, roadwork reduces movement speed compared with the normal OSM/SUMO road speed.

## Accident point

An accident point slows traffic near the selected location.

<div align="center">

<img src="assets/forreadme/14.png" alt="UrbanFlow AI accident point selection" width="600"/>

</div>

The accident effect is local and applies around the selected point.

## Applied editor events

The editor visualizes applied changes directly on the city scene.

<div align="center">

<img src="assets/forreadme/15.jpeg" alt="UrbanFlow AI applied road editor events" width="600"/>

</div>

Visual meanings:

- red glowing roads — manually blocked roads;
- green roads — explicitly opened roads;
- yellow glowing roads — roadwork;
- orange points — accident locations;
- red pedestrian-only roads — pedestrian or non-drivable access.

## View settings

The View panel controls scene quality and visualization layers.

<div align="center">

<img src="assets/forreadme/16.jpeg" alt="UrbanFlow AI view settings panel" width="600"/>

</div>

Available view settings include:

- shadows;
- high resolution rendering;
- depth precision mode;
- fine geometry details;
- detailed actor models;
- building rendering;
- ground zone colors;
- special zones;
- road access highlight;
- congestion highlight.

Most expensive visual features can be disabled to keep the simulation fast.

## Minimal rendering mode

The scene can run with lightweight rendering settings.

<div align="center">

<img src="assets/forreadme/17.png" alt="UrbanFlow AI minimal rendering mode close view" width="600"/>

</div>

This mode is useful for performance-focused simulation and training.

## Maximum visual detail

The scene can also render with more visual layers and detail enabled.

<div align="center">

<img src="assets/forreadme/18.png" alt="UrbanFlow AI detailed rendering mode overview" width="600"/>

</div>

<div align="center">

<img src="assets/forreadme/19.png" alt="UrbanFlow AI detailed rendering mode close view" width="600"/>

</div>

Detailed mode can show more buildings, zones, actors and geometry detail.

## Actor visualization modes

Vehicles can be rendered in simpler or more detailed forms depending on performance and visualization needs.

<table>
<tr>
<td align="center">
<img src="assets/forreadme/20.png" alt="UrbanFlow AI simple vehicle model" width="400"/>
</td>
<td align="center">
<img src="assets/forreadme/21.png" alt="UrbanFlow AI detailed vehicle model" width="400"/>
</td>
</tr>
</table>

Pedestrians also support a detailed display mode.

<div align="center">

<img src="assets/forreadme/22.png" alt="UrbanFlow AI detailed pedestrian model" width="600"/>

</div>

In simple mode, pedestrians can be displayed as lightweight markers. In detailed mode, they are shown with more visual structure.

## Road access visualization

Road access highlighting shows which parts of the network are available or restricted.

<div align="center">

<img src="assets/forreadme/23.jpeg" alt="UrbanFlow AI road access visualization overview" width="600"/>

</div>

<div align="center">

<img src="assets/forreadme/24.png" alt="UrbanFlow AI road access visualization close view" width="600"/>

</div>

Typical colors:

- pedestrian-only roads and paths are shown in red;
- manually closed roads use stronger red highlighting;
- roadwork uses yellow highlighting;
- accident locations are shown as yellow/orange points.

## Congestion visualization

Congestion highlighting shows traffic load on roads.

<div align="center">

<img src="assets/forreadme/25.jpeg" alt="UrbanFlow AI road congestion visualization overview" width="600"/>

</div>

<div align="center">

<img src="assets/forreadme/26.png" alt="UrbanFlow AI road congestion visualization close view" width="600"/>

</div>

Typical congestion colors:

- green — free traffic;
- yellow — medium load;
- red — high load.

## AI training panel

The Training panel configures visual training for the UrbanFlow AI controller.

<div align="center">

<img src="assets/forreadme/27.jpeg" alt="UrbanFlow AI training panel" width="600"/>

</div>

Training settings include:

- signal scope;
- OSM traffic lights only;
- all possible intersections;
- start vehicle count;
- maximum vehicle count;
- vehicle step;
- steps per level;
- pedestrian count;
- random road events during training;
- start visual training;
- stop training;
- save trained model;
- export checkpoint.

The training process runs on the active SUMO session. SUMO still controls the movement of vehicles and pedestrians. UrbanFlow AI controls only the traffic-light phase decisions.

## Visual training process

During training, the simulation keeps running visually and metrics are updated.

<div align="center">

<img src="assets/forreadme/28.jpeg" alt="UrbanFlow AI visual training process" width="600"/>

</div>

The training job records:

- current step;
- current episode;
- current vehicle count;
- best reward;
- latest reward;
- average waiting time;
- congestion score;
- stopped vehicles;
- checkpoint path;
- training run directory.

When a checkpoint is available, the model can be saved into the model registry.

## Public transport

UrbanFlow AI supports public transport artifacts and runtime vehicles when SUMO can build valid routes from OSM data.

Public transport support includes:

- bus stops;
- bus routes;
- trolleybus/minibus-style OSM routes when represented as compatible road routes;
- tram routes;
- rail-based tram movement where valid SUMO rail/tram edges exist;
- public transport vehicles that follow their routes;
- stop usage where valid stops are generated.

Public transport is not a visual fake layer. When spawned successfully, public transport vehicles are SUMO/TraCI vehicles and follow SUMO routes.

## Simulation modes

### SUMO automatic control

SUMO controls the traffic lights using its own signal programs.

Vehicles, pedestrians and public transport are still simulated by SUMO.

### Manual fixed cycle

The application applies a simple fixed-cycle traffic-light control strategy.

This mode is useful as a baseline.

### UrbanFlow AI control

UrbanFlow AI controls real SUMO traffic lights through TraCI.

When this mode is selected, the backend attempts to load the latest saved model for the current signal scope. If no saved model exists, the runtime controller uses its default JSON policy.

## AI observations and decisions

For each controlled SUMO traffic light, UrbanFlow AI can observe:

- controlled lanes;
- current phase;
- available phases;
- vehicle count;
- halted vehicle count;
- average speed;
- maximum speed;
- waiting time;
- occupancy;
- allowed and disallowed vehicle classes;
- pressure of the current phase;
- pressure of candidate phases.

The controller can:

- keep the current phase;
- switch to another green phase;
- avoid switching too often;
- enforce minimum green time;
- respond to high lane pressure;
- respond to excessive phase duration.

## Reward

The current reward function is calculated from SUMO-derived traffic metrics.

It can include:

- queue penalty;
- waiting-time penalty;
- stopped-vehicle penalty;
- congestion penalty;
- low-speed penalty;
- phase-switch penalty;
- throughput bonus.

The objective is to reduce waiting, reduce queues, reduce congestion and avoid chaotic traffic-light switching.

## Training artifacts and saved models

Training artifacts are written under:

    data/models/

Typical structure:

    data/models/tls_osm_only/
      runs/
        training_<id>/
          job.json
          training_history.csv
          training_history.jsonl
          latest_summary.json
          training_dashboard.md
          notebook_refresh.log
          checkpoints/
            best_model.json
          snapshots/
            checkpoint_step_00000120.json
      saved/
        model_<id>_training_<id>_step_00000150.json
        model_<id>_training_<id>_step_00000150.metadata.json
      exports/
        export_<id>_training_<id>_step_00000150.json
        export_<id>_training_<id>_step_00000150.metadata.json

For the all-intersections scope, artifacts are stored under:

    data/models/tls_all_intersections/

The `Save trained model` action copies the best checkpoint into the saved model registry.

The `Export checkpoint` action creates an additional checkpoint export for analysis or transfer.

## Generated notebooks

UrbanFlow AI generates Jupyter notebooks with embedded outputs.

Notebook files:

    ai/notebooks/01_explore_sumo_tls.ipynb
    ai/notebooks/02_reward_design.ipynb
    ai/notebooks/03_train_tls_agent.ipynb
    ai/notebooks/04_evaluate_tls_agent.ipynb

The notebooks can show:

- SUMO artifact counts;
- parsed debug metrics;
- traffic-light statistics;
- intersection complexity;
- reward sensitivity;
- reward surface;
- training history;
- rolling reward;
- average waiting time charts;
- congestion charts;
- stopped-vehicle charts;
- checkpoint summaries;
- saved model registry data.

The notebook generator can be run manually:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI/server && uv run python ../ai/notebooks/create_analysis_notebooks.py

The training artifact writer can also refresh notebooks automatically with a throttle.

## Local development

This project is intended to be run from source during development.

Install backend dependencies:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI/server && uv sync

Install frontend dependencies:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI/web && npm install

Run the development environment:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI && ./scripts/run-dev.sh

Open the frontend:

    http://127.0.0.1:5173

Useful port cleanup command:

    for port in 8000 8080 5173; do lsof -tiTCP:$port -sTCP:LISTEN | xargs kill -9 2>/dev/null || true; done

Frontend build check:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI/web && npm run build

Backend compile check:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI/server && uv run python -m py_compile app/simulation/sumo_engine.py app/simulation/sumo_scenario.py app/simulation/training_jobs.py app/simulation/ai_tls_controller.py

AI package import check:

    cd /Users/andrey/Documents/projects/UrbanFlow-AI && PYTHONPATH=ai python3 -m py_compile ai/urbanflow_ai/integration/runtime_controller.py ai/urbanflow_ai/env/sumo_tls_env.py ai/urbanflow_ai/models/policy.py

## Project structure

    UrbanFlow-AI/
    ├── ai/
    │   ├── notebooks/
    │   │   ├── 01_explore_sumo_tls.ipynb
    │   │   ├── 02_reward_design.ipynb
    │   │   ├── 03_train_tls_agent.ipynb
    │   │   ├── 04_evaluate_tls_agent.ipynb
    │   │   └── create_analysis_notebooks.py
    │   └── urbanflow_ai/
    │       ├── analysis/
    │       │   └── Training artifact and notebook refresh utilities
    │       ├── env/
    │       │   └── SUMO TLS environment, observations, actions and rewards
    │       ├── evaluation/
    │       │   └── Evaluation helpers
    │       ├── export/
    │       │   └── Checkpoint export helpers
    │       ├── integration/
    │       │   └── Runtime controller used by the backend
    │       ├── models/
    │       │   └── JSON policy and checkpoint logic
    │       ├── training/
    │       │   └── Curriculum and training helpers
    │       └── utils/
    │           └── Network metric utilities
    ├── assets/
    │   └── forreadme/
    │       └── README logos and screenshots
    ├── data/
    │   ├── models/
    │   │   ├── tls_osm_only/
    │   │   └── tls_all_intersections/
    │   ├── osm/
    │   ├── runs/
    │   └── sessions/
    ├── docs/
    │   └── urbanflow-ai-spec.md
    ├── scripts/
    │   ├── run-dev.sh
    │   ├── run-server.sh
    │   ├── run-web.sh
    │   ├── test-server.sh
    │   └── test-web.sh
    ├── server/
    │   ├── app/
    │   │   ├── api/
    │   │   │   └── FastAPI routes for OSM, simulation, editor and training
    │   │   ├── core/
    │   │   │   └── Backend configuration
    │   │   ├── osm/
    │   │   │   └── OSM client, parser and normalizer
    │   │   ├── schemas/
    │   │   │   └── Pydantic schemas
    │   │   ├── simulation/
    │   │   │   └── SUMO engine, TraCI control, metrics, events and training jobs
    │   │   └── utils/
    │   │       └── Geo utilities
    │   ├── pyproject.toml
    │   └── uv.lock
    ├── tests/
    │   ├── server/
    │   └── web/
    └── web/
        ├── src/
        │   ├── api/
        │   │   └── API client
        │   ├── components/
        │   │   └── UI panels and controls
        │   ├── scene/
        │   │   └── 3D city scene and actors
        │   ├── styles/
        │   │   └── Global CSS
        │   ├── types/
        │   │   └── Domain and scene types
        │   └── utils/
        │       └── Formatting utilities
        ├── package.json
        └── vite.config.ts

## Notes

UrbanFlow AI focuses on real simulation behavior rather than purely visual animation.

Important implementation points:

- SUMO controls vehicle motion;
- SUMO controls pedestrian motion;
- SUMO controls public transport motion when routes are valid;
- vehicles obey SUMO traffic lights;
- UrbanFlow AI controls traffic-light phases only when AI mode is selected;
- fixed/manual algorithms also control traffic lights through the simulation layer;
- vehicles still remain SUMO-controlled in every traffic-light mode;
- OSM data quality affects generated roads, buildings, routes and public transport;
- not every OSM area contains enough usable traffic-light, public-transport or building data.

The project is a working technical prototype and a foundation for further traffic simulation, AI control, urban analytics and reinforcement learning experiments.