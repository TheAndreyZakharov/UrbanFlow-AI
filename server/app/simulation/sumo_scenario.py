import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from app.schemas.osm import CityMapDto


SUMO_ROUTE_VTYPES = """
<vType id="car" vClass="passenger" length="4.4" width="1.8" minGap="2.8" accel="2.4" decel="4.5" tau="1.0" sigma="0.45" maxSpeed="33.33"/>
<vType id="taxi" vClass="taxi" length="4.4" width="1.8" minGap="2.6" accel="2.5" decel="4.6" tau="0.9" sigma="0.4" maxSpeed="33.33"/>
<vType id="truck" vClass="truck" length="8.5" width="2.5" minGap="4.2" accel="1.1" decel="4.0" tau="1.2" sigma="0.55" maxSpeed="25.00"/>
<vType id="bus" vClass="bus" length="10.5" width="2.5" minGap="4.4" accel="1.0" decel="4.0" tau="1.25" sigma="0.4" maxSpeed="22.22"/>
<vType id="tram" vClass="tram" length="22.0" width="2.4" minGap="5.5" accel="0.9" decel="3.0" tau="1.4" sigma="0.2" maxSpeed="16.67"/>
<vType id="light_rail" vClass="rail_urban" length="32.0" width="2.65" minGap="7.0" accel="0.8" decel="2.8" tau="1.5" sigma="0.2" maxSpeed="22.22"/>
<vType id="train" vClass="rail" length="80.0" width="2.9" minGap="12.0" accel="0.55" decel="2.2" tau="1.8" sigma="0.15" maxSpeed="27.78"/>
<vType id="emergency" vClass="emergency" length="5.0" width="2.1" minGap="2.2" accel="3.0" decel="5.0" tau="0.75" sigma="0.25" maxSpeed="38.89"/>
"""


class SumoScenarioError(RuntimeError):
    pass


def clean_sumo_workspace() -> None:
    for path in [
        Path("data") / "sumo",
        Path("server") / "data" / "sumo",
    ]:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)


def ensure_sumo_python_tools() -> None:
    sumo_home = find_sumo_home()

    if sumo_home is not None:
        os.environ["SUMO_HOME"] = str(sumo_home)
    proj_db_path = find_proj_db()

    if proj_db_path is not None:
        os.environ["PROJ_LIB"] = str(proj_db_path.parent)

    candidate_paths = []

    if sumo_home is not None:
        candidate_paths.append(sumo_home / "tools")

    candidate_paths.extend(
        [
            Path("/opt/homebrew/opt/sumo/share/sumo/tools"),
            Path("/usr/local/opt/sumo/share/sumo/tools"),
            Path("/Applications/SUMO.app/Contents/Resources/share/sumo/tools"),
            Path("/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO/tools"),
            Path("/Library/Frameworks/EclipseSUMO.framework/Versions/1.27.0/EclipseSUMO/tools"),
        ]
    )

    for path in candidate_paths:
        if path.exists() and str(path) not in sys.path:
            sys.path.append(str(path))


def find_sumo_home() -> Path | None:
    env_sumo_home = os.environ.get("SUMO_HOME")
    candidates: list[Path] = []

    if env_sumo_home:
        candidates.append(Path(env_sumo_home))

    candidates.extend(
        [
            Path("/opt/homebrew/opt/sumo/share/sumo"),
            Path("/usr/local/opt/sumo/share/sumo"),
            Path("/Applications/SUMO.app/Contents/Resources/share/sumo"),
            Path("/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO"),
            Path("/Library/Frameworks/EclipseSUMO.framework/Versions/1.27.0/EclipseSUMO"),
        ]
    )

    for candidate in candidates:
        if (candidate / "data" / "typemap" / "osmNetconvert.typ.xml").exists():
            return candidate

        nested = candidate / "share" / "sumo"
        if (nested / "data" / "typemap" / "osmNetconvert.typ.xml").exists():
            return nested

    for root in [
        Path("/Library/Frameworks/EclipseSUMO.framework"),
        Path("/opt/homebrew"),
        Path("/usr/local"),
        Path("/Applications"),
    ]:
        if not root.exists():
            continue

        try:
            for typemap_path in root.rglob("osmNetconvert.typ.xml"):
                if typemap_path.parent.name == "typemap" and typemap_path.parent.parent.name == "data":
                    return typemap_path.parent.parent.parent
        except OSError:
            continue

    return None


def sumo_typemap_path() -> Path:
    sumo_home = find_sumo_home()

    if sumo_home is None:
        raise SumoScenarioError("Could not find SUMO_HOME automatically.")

    typemap_path = sumo_home / "data" / "typemap" / "osmNetconvert.typ.xml"

    if not typemap_path.exists():
        raise SumoScenarioError(f"SUMO typemap was not found at {typemap_path}")

    return typemap_path


def sumo_environment() -> dict[str, str]:
    environment = os.environ.copy()
    sumo_home = find_sumo_home()

    if sumo_home is not None:
        environment["SUMO_HOME"] = str(sumo_home)

        tools_path = str(sumo_home / "tools")
        current_python_path = environment.get("PYTHONPATH", "")

        if current_python_path:
            environment["PYTHONPATH"] = f"{tools_path}{os.pathsep}{current_python_path}"
        else:
            environment["PYTHONPATH"] = tools_path
    proj_db_path = find_proj_db()

    if proj_db_path is not None:
        environment["PROJ_LIB"] = str(proj_db_path.parent)
    return environment

def find_proj_db() -> Path | None:
    env_proj_lib = os.environ.get("PROJ_LIB")

    if env_proj_lib:
        candidate = Path(env_proj_lib) / "proj.db"

        if candidate.exists():
            return candidate

    preferred = Path("/opt/homebrew/Cellar/proj/9.6.2/share/proj/proj.db")

    if preferred.exists():
        return preferred

    for root in [
        Path("/opt/homebrew/Cellar/proj"),
        Path("/Library/Frameworks/EclipseSUMO.framework"),
        Path("/opt/homebrew"),
        Path("/usr/local"),
        Path("/Applications"),
    ]:
        if not root.exists():
            continue

        try:
            for proj_db_path in root.rglob("proj.db"):
                return proj_db_path
        except OSError:
            continue

    return None

def require_binary(name: str) -> str:
    binary = shutil.which(name)

    if binary is None:
        raise SumoScenarioError(f"SUMO binary '{name}' was not found in PATH.")

    return binary


async def build_sumo_scenario(
    city_map: CityMapDto,
    session_id: str,
    vehicles_count: int,
    pedestrians_count: int,
    signals_on_all_intersections: bool,
) -> Path:
    scenario_dir = Path("data") / "sumo" / safe_file_name(session_id)

    if scenario_dir.exists():
        shutil.rmtree(scenario_dir, ignore_errors=True)

    scenario_dir.mkdir(parents=True, exist_ok=True)

    osm_path = scenario_dir / "map.osm.xml"
    base_net_path = scenario_dir / "map.base.net.xml"
    net_path = scenario_dir / "map.net.xml"
    trips_path = scenario_dir / "trips.trips.xml"
    pedestrians_path = scenario_dir / "pedestrians.trips.xml"
    routes_path = scenario_dir / "routes.rou.xml"
    pt_stops_path = scenario_dir / "public_transport.add.xml"
    pt_lines_path = scenario_dir / "public_transport_lines.xml"
    pt_routes_path = scenario_dir / "public_transport.rou.xml"
    all_routes_path = scenario_dir / "all_routes.rou.xml"
    config_path = scenario_dir / "simulation.sumocfg"

    await download_osm_xml(city_map=city_map, output_path=osm_path)

    build_network(
        osm_path=osm_path,
        net_path=base_net_path,
        pt_stops_path=pt_stops_path,
        pt_lines_path=pt_lines_path,
        tls_junction_ids=[],
    )

    tls_junction_ids = []

    if signals_on_all_intersections:
        tls_junction_ids = junction_ids_for_city_intersections(
            net_path=base_net_path,
            city_map=city_map,
        )

    if tls_junction_ids:
        tls_junction_ids = build_network_with_safe_tls_set(
            osm_path=osm_path,
            net_path=net_path,
            pt_stops_path=pt_stops_path,
            pt_lines_path=pt_lines_path,
            tls_junction_ids=tls_junction_ids,
        )
    else:
        shutil.copyfile(base_net_path, net_path)

    build_vehicle_trips(
        net_path=net_path,
        trips_path=trips_path,
        vehicles_count=vehicles_count,
    )

    build_pedestrian_trips(
        net_path=net_path,
        pedestrians_path=pedestrians_path,
        pedestrians_count=pedestrians_count,
    )

    build_routes(
        net_path=net_path,
        trips_path=trips_path,
        pedestrians_path=pedestrians_path,
        routes_path=routes_path,
    )

    build_public_transport_routes(
        net_path=net_path,
        pt_stops_path=pt_stops_path,
        pt_lines_path=pt_lines_path,
        pt_routes_path=pt_routes_path,
    )

    merge_route_files(
        output_path=all_routes_path,
        route_files=[routes_path, pt_routes_path],
    )

    build_config(
        net_path=net_path,
        routes_path=all_routes_path,
        pt_stops_path=pt_stops_path,
        config_path=config_path,
    )

    write_scenario_debug(
        scenario_dir=scenario_dir,
        net_path=net_path,
        routes_path=all_routes_path,
        pt_stops_path=pt_stops_path,
        pt_lines_path=pt_lines_path,
        pt_routes_path=pt_routes_path,
        tls_junction_ids=tls_junction_ids,
    )

    return config_path


async def download_osm_xml(city_map: CityMapDto, output_path: Path) -> None:
    bbox = city_map.bbox
    bbox_string = f"{bbox.south},{bbox.west},{bbox.north},{bbox.east}"

    query = f"""
[out:xml][timeout:180];
(
  nwr["highway"]({bbox_string});
  nwr["railway"]({bbox_string});
  nwr["public_transport"]({bbox_string});
  node["highway"="bus_stop"]({bbox_string});
  way["highway"="bus_stop"]({bbox_string});
  node["highway"="traffic_signals"]({bbox_string});
  node["highway"="crossing"]({bbox_string});
  way["footway"="crossing"]({bbox_string});
  relation["type"="route"]["route"~"^(bus|tram|trolleybus|share_taxi|minibus|coach|train|light_rail)$"]({bbox_string});
  relation["type"="route_master"]["route_master"~"^(bus|tram|trolleybus|share_taxi|minibus|coach|train|light_rail)$"]({bbox_string});
);
(._; >;);
out body;
""".strip()

    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "application/xml",
        "User-Agent": "UrbanFlow-AI/0.1 local-development",
    }

    errors = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=25.0, read=180.0, write=25.0, pool=25.0)) as client:
        for endpoint in endpoints:
            try:
                response = await client.post(endpoint, data={"data": query}, headers=headers)

                if response.status_code in {429, 500, 502, 503, 504}:
                    errors.append(f"{endpoint} -> HTTP {response.status_code}")
                    continue

                response.raise_for_status()

                if "<osm" not in response.text:
                    errors.append(f"{endpoint} -> invalid OSM XML")
                    continue

                output_path.write_text(response.text, encoding="utf-8")
                return
            except Exception as error:
                errors.append(f"{endpoint} -> {error!r}")

    raise SumoScenarioError("Could not download OSM XML for SUMO. " + " | ".join(errors))


def build_network_with_safe_tls_set(
    osm_path: Path,
    net_path: Path,
    pt_stops_path: Path,
    pt_lines_path: Path,
    tls_junction_ids: list[str],
) -> list[str]:
    if not tls_junction_ids:
        build_network(
            osm_path=osm_path,
            net_path=net_path,
            pt_stops_path=pt_stops_path,
            pt_lines_path=pt_lines_path,
            tls_junction_ids=[],
        )
        return []

    attempts = [
        tls_junction_ids,
        tls_junction_ids[:800],
        tls_junction_ids[:500],
        tls_junction_ids[:300],
        tls_junction_ids[:180],
        tls_junction_ids[:100],
    ]

    last_error: Exception | None = None

    for attempt_ids in attempts:
        if not attempt_ids:
            continue

        try:
            build_network(
                osm_path=osm_path,
                net_path=net_path,
                pt_stops_path=pt_stops_path,
                pt_lines_path=pt_lines_path,
                tls_junction_ids=attempt_ids,
            )
            return attempt_ids
        except Exception as error:
            last_error = error

    raise SumoScenarioError(
        "Could not build SUMO network with all-intersections traffic lights. "
        f"Initial TLS candidates: {len(tls_junction_ids)}. "
        f"Last error: {last_error!r}"
    )

def build_network(
    osm_path: Path,
    net_path: Path,
    pt_stops_path: Path,
    pt_lines_path: Path,
    tls_junction_ids: list[str],
) -> None:
    netconvert = require_binary("netconvert")
    typemap_path = sumo_typemap_path()

    command = [
        netconvert,
        "--osm-files",
        str(osm_path),
        "--type-files",
        str(typemap_path),
        "--output-file",
        str(net_path),
        "--geometry.remove",
        "true",
        "--roundabouts.guess",
        "true",
        "--ramps.guess",
        "true",
        "--junctions.join",
        "true",
        "--tls.guess",
        "true",
        "--tls.guess-signals",
        "true",
        "--tls.discard-simple",
        "false",
        "--tls.default-type",
        "actuated",
        "--crossings.guess",
        "true",
        "--sidewalks.guess",
        "true",
        "--osm.stop-output.length",
        "20",
        "--ptstop-output",
        str(pt_stops_path),
        "--ptline-output",
        str(pt_lines_path),
        "--osm.all-attributes",
        "true",
        "--no-warnings",
        "true",
    ]

    if tls_junction_ids:
        command.extend(["--tls.set", ",".join(tls_junction_ids)])

    run_command(command)


def junction_ids_for_city_intersections(net_path: Path, city_map: CityMapDto) -> list[str]:
    try:
        tree = ET.parse(net_path)
    except ET.ParseError:
        return []

    junctions: list[tuple[str, float, float, int, int]] = []

    for junction in tree.getroot().findall("junction"):
        junction_id = junction.get("id", "")

        if not junction_id or junction_id.startswith(":"):
            continue

        junction_type = junction.get("type", "")

        if junction_type in {"internal", "dead_end", "rail_crossing"}:
            continue

        incoming_lanes = [
            lane_id
            for lane_id in junction.get("incLanes", "").split()
            if lane_id and not lane_id.startswith(":")
        ]
        internal_lanes = [
            lane_id
            for lane_id in junction.get("intLanes", "").split()
            if lane_id
        ]

        incoming_edge_ids = {
            lane_id.rsplit("_", 1)[0]
            for lane_id in incoming_lanes
            if "_" in lane_id
        }

        if len(incoming_edge_ids) < 2:
            continue

        if len(internal_lanes) < 1:
            continue

        try:
            x = float(junction.get("x", "0"))
            y = float(junction.get("y", "0"))
        except ValueError:
            continue

        junctions.append(
            (
                junction_id,
                x,
                y,
                len(incoming_edge_ids),
                len(incoming_lanes),
            )
        )

    if not junctions:
        return []

    result: set[str] = set()

    for intersection in city_map.intersections:
        best_id = None
        best_distance = 999999999.0

        target_x = -intersection.x
        target_y = intersection.z

        for junction_id, x, y, _incoming_edge_count, _incoming_lane_count in junctions:
            distance = ((x - target_x) ** 2 + (y - target_y) ** 2) ** 0.5

            if distance < best_distance:
                best_distance = distance
                best_id = junction_id

        if best_id is not None and best_distance <= 90:
            result.add(best_id)

    if result:
        return sorted(result)

    junctions.sort(
        key=lambda item: (
            item[3],
            item[4],
        ),
        reverse=True,
    )

    return [
        junction_id
        for junction_id, _x, _y, _incoming_edge_count, _incoming_lane_count in junctions
    ]


def build_vehicle_trips(net_path: Path, trips_path: Path, vehicles_count: int) -> None:
    trips_path.write_text("<routes>\n</routes>\n", encoding="utf-8")


def build_pedestrian_trips(net_path: Path, pedestrians_path: Path, pedestrians_count: int) -> None:
    if pedestrians_count <= 0:
        pedestrians_path.write_text("<routes>\n</routes>\n", encoding="utf-8")
        return

    random_trips = sumo_tool("randomTrips.py")
    pedestrian_period = max(1.0, 900 / max(1, pedestrians_count))

    command = [
        sys.executable,
        random_trips,
        "--net-file",
        str(net_path),
        "--output-trip-file",
        str(pedestrians_path),
        "--begin",
        "0",
        "--end",
        "900",
        "--period",
        str(pedestrian_period),
        "--pedestrians",
        "--persontrips",
        "--validate",
        "--remove-loops",
        "--prefix",
        "ped_",
    ]

    run_command(command)


def build_routes(net_path: Path, trips_path: Path, pedestrians_path: Path, routes_path: Path) -> None:
    duarouter = require_binary("duarouter")
    merged_path = routes_path.with_name("merged.trips.xml")

    merged_path.write_text(
        "<routes>\n"
        f"{SUMO_ROUTE_VTYPES}\n"
        f"{read_route_children(trips_path)}\n"
        f"{read_route_children(pedestrians_path)}\n"
        "</routes>\n",
        encoding="utf-8",
    )

    command = [
        duarouter,
        "--net-file",
        str(net_path),
        "--route-files",
        str(merged_path),
        "--output-file",
        str(routes_path),
        "--ignore-errors",
        "true",
        "--repair",
        "true",
        "--no-warnings",
        "true",
    ]

    run_command(command)


def build_public_transport_routes(
    net_path: Path,
    pt_stops_path: Path,
    pt_lines_path: Path,
    pt_routes_path: Path,
) -> None:
    ptlines2flows = sumo_tool("ptlines2flows.py")

    if not pt_stops_path.exists() or not pt_lines_path.exists():
        pt_routes_path.write_text("<routes>\n</routes>\n", encoding="utf-8")
        return

    command = [
        sys.executable,
        ptlines2flows,
        "-n",
        str(net_path),
        "-s",
        str(pt_stops_path),
        "-l",
        str(pt_lines_path),
        "-o",
        str(pt_routes_path),
        "-p",
        "300",
        "--use-osm-routes",
        "--ignore-errors",
        "--no-warnings",
    ]

    try:
        run_command(command)
        normalize_public_transport_routes(pt_routes_path)
    except SumoScenarioError:
        pt_routes_path.write_text("<routes>\n</routes>\n", encoding="utf-8")


def normalize_public_transport_routes(pt_routes_path: Path) -> None:
    if not pt_routes_path.exists():
        return

    try:
        tree = ET.parse(pt_routes_path)
    except ET.ParseError:
        pt_routes_path.write_text("<routes>\n</routes>\n", encoding="utf-8")
        return

    root = tree.getroot()

    for element in root.iter():
        if element.tag not in {"vehicle", "flow"}:
            continue

        transit_type = public_transport_type_for_element(element)

        element.set("id", public_transport_id(element))
        element.set("type", transit_type)
        element.set("departLane", "best")
        element.set("departSpeed", "max")

        if element.tag == "flow":
            element.set("period", "300")
            element.set("begin", element.get("begin", "0"))
            element.set("end", element.get("end", "86400"))

    tree.write(pt_routes_path, encoding="utf-8", xml_declaration=True)


def public_transport_type_for_element(element: ET.Element) -> str:
    text = " ".join(
        [
            element.get("id", ""),
            element.get("type", ""),
            element.get("line", ""),
            element.get("from", ""),
            element.get("to", ""),
        ]
    ).lower()

    if "tram" in text:
        return "tram"

    if "light_rail" in text:
        return "light_rail"

    if "train" in text or "rail" in text:
        return "train"

    return "bus"


def public_transport_id(element: ET.Element) -> str:
    original_id = element.get("id", "vehicle")
    cleaned = safe_file_name(original_id)

    if cleaned.startswith("pt_"):
        return cleaned

    return f"pt_{cleaned}"


def merge_route_files(output_path: Path, route_files: list[Path]) -> None:
    children = [SUMO_ROUTE_VTYPES]

    for route_file in route_files:
        children.append(read_route_children(route_file, skip_type_definitions=True))

    output_path.write_text(
        "<routes>\n" + "\n".join(child for child in children if child.strip()) + "\n</routes>\n",
        encoding="utf-8",
    )


def build_config(
    net_path: Path,
    routes_path: Path,
    pt_stops_path: Path,
    config_path: Path,
) -> None:
    additional_files = []

    if pt_stops_path.exists():
        additional_files.append(pt_stops_path.name)

    config_path.write_text(
        f"""<configuration>
  <input>
    <net-file value="{net_path.name}"/>
    <route-files value="{routes_path.name}"/>
    <additional-files value="{','.join(additional_files)}"/>
  </input>
  <time>
    <begin value="0"/>
    <end value="86400"/>
    <step-length value="1"/>
  </time>
  <processing>
    <collision.action value="warn"/>
    <collision.check-junctions value="true"/>
    <ignore-route-errors value="true"/>
    <pedestrian.model value="striping"/>
    <time-to-teleport value="45"/>
  </processing>
  <report>
    <verbose value="false"/>
    <no-step-log value="true"/>
    <no-warnings value="true"/>
  </report>
</configuration>
""",
        encoding="utf-8",
    )


def read_route_children(path: Path, skip_type_definitions: bool = False) -> str:
    if not path.exists():
        return ""

    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except ET.ParseError:
        return ""

    result = []

    for child in root:
        if skip_type_definitions and child.tag in {"vType", "vTypeDistribution"}:
            continue

        result.append(ET.tostring(child, encoding="unicode"))

    return "\n".join(result)


def write_scenario_debug(
    scenario_dir: Path,
    net_path: Path,
    routes_path: Path,
    pt_stops_path: Path,
    pt_lines_path: Path,
    pt_routes_path: Path,
    tls_junction_ids: list[str],
) -> None:
    debug_path = scenario_dir / "debug.txt"

    debug_path.write_text(
        "\n".join(
            [
                f"net={net_path}",
                f"routes={routes_path}",
                f"pt_stops={pt_stops_path}",
                f"pt_lines={pt_lines_path}",
                f"pt_routes={pt_routes_path}",
                f"tls_junction_count={len(tls_junction_ids)}",
                f"sumo_net_tls_count={count_sumo_net_traffic_lights(net_path)}",
                f"tls_junction_ids={','.join(tls_junction_ids[:300])}",
                f"route_vehicle_count={count_xml_tags(routes_path, 'vehicle')}",
                f"route_flow_count={count_xml_tags(routes_path, 'flow')}",
                f"route_person_count={count_xml_tags(routes_path, 'person')}",
                f"pt_stop_count={count_xml_tags(pt_stops_path, 'busStop') + count_xml_tags(pt_stops_path, 'trainStop')}",
                f"pt_vehicle_count={count_xml_tags(pt_routes_path, 'vehicle')}",
                f"pt_flow_count={count_xml_tags(pt_routes_path, 'flow')}",
                f"pt_period_300_only={public_transport_period_is_exactly_300(pt_routes_path)}",
            ]
        ),
        encoding="utf-8",
    )

def count_sumo_net_traffic_lights(path: Path) -> int:
    if not path.exists():
        return 0

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return 0

    return sum(
        1
        for junction in root.findall("junction")
        if junction.get("type") == "traffic_light"
    )

def count_xml_tags(path: Path, tag: str) -> int:
    if not path.exists():
        return 0

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return 0

    return sum(1 for _ in root.iter(tag))


def sumo_tool(name: str) -> str:
    ensure_sumo_python_tools()

    candidate_paths = []

    for path in sys.path:
        candidate_paths.append(Path(path) / name)

    sumo_home = os.environ.get("SUMO_HOME")

    if sumo_home:
        candidate_paths.append(Path(sumo_home) / "tools" / name)

    candidate_paths.extend(
        [
            Path("/opt/homebrew/opt/sumo/share/sumo/tools") / name,
            Path("/usr/local/opt/sumo/share/sumo/tools") / name,
            Path("/Applications/SUMO.app/Contents/Resources/share/sumo/tools") / name,
            Path("/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO/tools") / name,
            Path("/Library/Frameworks/EclipseSUMO.framework/Versions/1.27.0/EclipseSUMO/tools") / name,
        ]
    )

    for path in candidate_paths:
        if path.exists():
            return str(path)

    raise SumoScenarioError(f"SUMO tool '{name}' was not found. Check SUMO_HOME.")


def run_command(command: list[str]) -> None:
    result = subprocess.run(
        command,
        cwd=None,
        text=True,
        capture_output=True,
        env=sumo_environment(),
    )

    if result.returncode != 0:
        raise SumoScenarioError(
            "SUMO command failed:\n"
            + " ".join(command)
            + "\nSUMO_HOME:\n"
            + str(sumo_environment().get("SUMO_HOME", "<not set>"))
            + "\nSTDOUT:\n"
            + result.stdout[-5000:]
            + "\nSTDERR:\n"
            + result.stderr[-5000:]
        )

def public_transport_period_is_exactly_300(path: Path) -> bool:
    if not path.exists():
        return False

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return False

    flows = list(root.iter("flow"))

    if not flows:
        return False

    for flow in flows:
        if flow.get("period") != "300":
            return False

    return True

def safe_file_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)