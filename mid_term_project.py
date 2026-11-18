import marimo

__generated_with = "0.25.2"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # A Spatial and Functional Analysis of Electric Vehicle Charging Infrastructure: A Case Study of Styria
    Inspired by A Spatial and Functional Analysis of Electric Vehicle Charging Infrastructure: A Case Study of Lombardy (FEDERICO SILVESTRI AND MICHELA LONGO, 2026)
    """)
    return


@app.cell
def _():
    import osmnx as ox
    import marimo as mo
    import openpyxl
    import pandas as pd
    import geopandas as gpd
    import numpy as np
    import h3
    import plotly.express as px
    import os
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    import leafmap.kepler as leafmap
    from sklearn.cluster import DBSCAN
    from shapely.geometry import Polygon, box, MultiPoint
    from pathlib import Path
    from urllib.parse import urlencode
    from urllib.request import urlopen
    from datetime import datetime, timezone
    import seaborn as sns

    return Line2D, Polygon, gpd, h3, mo, np, os, ox, pd, plt, sns


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Data Acquisition
    ### Boundary of Styria
    """)
    return


@app.cell
def _(ox):
    boundary = ox.geocode_to_gdf("Steiermark, Austria")
    return (boundary,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Charging Stations
    """)
    return


@app.cell
def _(boundary, gpd, pd):
    stations = pd.read_excel(
        "data/Ladepunktdaten.xlsx",
        engine="openpyxl"
    )
    charging_stations = gpd.GeoDataFrame(stations, geometry=gpd.points_from_xy(stations.Longitude, stations.Latitude), crs="EPSG:4326")
    steiermark_boundary = boundary.geometry.union_all()
    charging_stations = charging_stations[
        charging_stations.geometry.within(steiermark_boundary)
    ].copy()

    print(f"Charging stations inside Styria: {len(charging_stations)}")
    charging_stations
    return (charging_stations,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Points of Interests (POI)
    """)
    return


@app.cell
def _(os, ox):
    def get_POI(amenity, boundary):
        tags = {"amenity": amenity}
        gdf = ox.features_from_polygon(
            boundary,
            tags
        )
        os.makedirs("data", exist_ok=True)
        # Save as GeoPackage
        filepath = f"data/{amenity}.geojson"
        gdf.to_file(filepath, driver="GeoJSON")

        print(f"Saved {len(gdf)} {amenity} features to {filepath}")

        return gdf

    return


@app.cell
def _():
    #hospitals = get_POI("hospital", steiermark_boundary)
    #clinics = get_POI("clinic", steiermark_boundary)
    #universities = get_POI("university", steiermark_boundary)
    return


@app.cell
def _(gpd):
    hospitals = gpd.read_file("data/hospital.geojson")
    clinics = gpd.read_file("data/clinic.geojson")
    universities = gpd.read_file("data/university.geojson")
    return clinics, hospitals, universities


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Municipalities of Styria
    """)
    return


@app.cell
def _(gpd, pd):
    municipalities = gpd.read_file("data/municipalites.geojson")
    mask = municipalities["admin_level"] == "9"

    # Dissolve all admin_level 9 features
    merged = municipalities.loc[mask].dissolve()

    # Set the attributes of the merged feature
    merged["admin_level"] = "8"
    merged["name"] = "Graz"
    merged["ref:at:gkz"] = "60101"

    # Combine with all remaining features
    municipalities = gpd.GeoDataFrame(
        pd.concat([
            municipalities.loc[~mask],
            merged
        ], ignore_index=True),
        crs=municipalities.crs
    )
    municipalities = municipalities[
        municipalities["type"] == "boundary"
    ].copy()
    municipalities = municipalities[["name", "ref:at:gkz", "geometry"]].copy()
    municipalities.rename(columns={"ref:at:gkz": "gkz"}, inplace=True)
    municipalities
    return (municipalities,)


@app.cell
def _(mo):
    mo.md(r"""
    ### Pop data
    """)
    return


@app.cell
def _(pd):
    pop_data = pd.read_csv("data/gemeinden.CSV", sep=";", encoding="cp1252", skiprows=9, names=["gkz", "name", "population"])
    pop_data.rename(columns={"0": "gkz", "1":"municipality","2":"population"}, inplace=True)
    pop_data.dropna(subset=["gkz"], inplace=True)
    pop_data["gkz"] = pop_data["gkz"].astype(str).str.split('.').str[0]
    pop_data
    return (pop_data,)


@app.cell
def _(municipalities, pop_data):
    cities = municipalities.merge(pop_data[["gkz", "population"]], on="gkz", how="left")
    cities
    return (cities,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Street Network of Styria
    Retrieved via geofabrik.de (17.11.2026 & processed in QGIS), Overpass-Query couldn't handle the request
    """)
    return


@app.cell
def _():
    '''
    # OSMnx settings
    ox.settings.requests_timeout = 800
    ox.settings.overpass_url = "https://overpass.private.coffee/api"

    # Define road filter
    cf = '["highway"~"motorway|trunk|primary|secondary"]'

    # Create output directory
    os.makedirs("data/output", exist_ok=True)

    # Download road network for Styria
    G = ox.graph_from_place(
        "Steiermark, Austria",
        network_type="drive",
        custom_filter=cf,
        simplify=True
    )

    # Save graph
    ox.save_graphml(
        G,
        filepath="data/output/styria.graphml"
    )
    '''
    return


@app.cell
def _(gpd):
    streets = gpd.read_file("data\streets.geojson")
    return (streets,)


@app.cell
def _(boundary):
    CRS = boundary.estimate_utm_crs()
    print(f"Estimated UTM CRS for all: {CRS}")
    return (CRS,)


@app.function
def project_to_utm(gdf, crs):
    return gdf.to_crs(crs)


@app.cell
def _(
    CRS,
    boundary,
    charging_stations,
    cities,
    clinics,
    hospitals,
    streets,
    universities,
):
    boundary_utm = project_to_utm(boundary, CRS)
    streets_utm = project_to_utm(streets, CRS)
    charging_stations_utm = project_to_utm(charging_stations, CRS)
    universities_utm = project_to_utm(universities, CRS)
    clinics_utm = project_to_utm(clinics, CRS)
    hospitals_utm = project_to_utm(hospitals, CRS)
    cities_utm = project_to_utm(cities, CRS)
    return (
        boundary_utm,
        charging_stations_utm,
        cities_utm,
        clinics_utm,
        hospitals_utm,
        streets_utm,
        universities_utm,
    )


@app.cell
def _(
    boundary_utm,
    charging_stations_utm,
    cities_utm,
    clinics_utm,
    hospitals_utm,
    streets_utm,
    universities_utm,
):
    print(f" CRS of boundary:", boundary_utm.crs)
    print(f" CRS of charging stations:", charging_stations_utm.crs)
    print(f" CRS of hospitals:", hospitals_utm.crs)
    print(f" CRS of clinics:", clinics_utm.crs)
    print(f" CRS of universities:", universities_utm.crs)
    print(f" CRS of streets:", streets_utm.crs)
    print(f" CRS of cities:", cities_utm.crs)
    return


@app.cell
def _(CRS, clinics_utm, gpd, hospitals_utm, pd, universities_utm):
    pois_utm = gpd.GeoDataFrame(
        pd.concat([universities_utm, clinics_utm, hospitals_utm], ignore_index=True),
        crs=CRS
    )
    print(f" CRS of POIs:", pois_utm.crs)
    return (pois_utm,)


@app.cell
def _(pois_utm):
    pois_centroids = pois_utm.copy()

    pois_centroids.geometry = pois_utm.geometry.centroid
    return (pois_centroids,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### First overview
    """)
    return


@app.cell
def _(
    boundary_utm,
    charging_stations_utm,
    cities_utm,
    plt,
    pois_centroids,
    streets_utm,
):
    fig, axis = plt.subplots(figsize=(20, 20))

    # Plot boundary
    boundary_utm.plot(
        ax=axis,
        facecolor="none",
        edgecolor="black",
        zorder=1
    )

    cities_utm.plot(
        ax=axis,
        facecolor="none",
        edgecolor="black",
        linewidth=0.5,
        zorder=2
    )

    # Define road classes
    road_classes = {
        "Highways": ["motorway", "motorway_link"],
        "Trunks": ["trunk", "trunk_link"],
        "Primary roads": ["primary", "primary_link"],
        "Secondary roads": ["secondary", "secondary_link"]
    }

    # Define colours and line widths
    road_styles = {
        "Highways": {"color": "red", "linewidth": 2},
        "Trunks": {"color": "orange", "linewidth": 1.5},
        "Primary roads": {"color": "gold", "linewidth": 1},
        "Secondary roads": {"color": "grey", "linewidth": 0.5}
    }

    # Plot roads
    for road, types in road_classes.items():
        streets_utm[streets_utm["fclass"].isin(types)].plot(
            ax=axis,
            label=road,
            zorder=3,
            alpha=0.7,
            **road_styles[road]
        )

    # Plot POIs
    pois_centroids.plot(
        ax=axis,
        markersize=8,
        color="blue",
        edgecolor="black",
        linewidth=0.3,
        label="POIs",
        zorder=4
    )

    # Plot charging stations
    charging_stations_utm.plot(
        ax=axis,
        markersize=10,
        color="red",
        edgecolor="black",
        label="Charging Stations",
        alpha=0.8,
        zorder=5
    )


    # Formatting
    axis.legend(loc="best", fontsize=12)
    axis.set_axis_off()
    axis.set_aspect("equal")

    plt.tight_layout()
    plt.show()
    return (road_classes,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Statistical Analysis
    ### Examine Population vs Nr. of charging stations
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    für jede Gemeinde:
       Zähle Ladestationen innerhalb Gemeinde
       neue Column für Anzahl/ pro gemeinde -->
       Plot Anzahl / pro Gemeinde zu EW
    """)
    return


@app.function
def count_charging_stations_for_municipality(name, municipalities_gdf, charging_stations_gdf):
    # Filter the municipality by name
    municipality = municipalities_gdf[municipalities_gdf['name'] == name]

    if municipality.empty:
        print(f"Municipality '{name}' not found.")
        return 0

    # Get the geometry of the municipality
    municipality_geometry = municipality.iloc[0].geometry

    # Count charging stations within the municipality geometry
    count = charging_stations_gdf[charging_stations_gdf.geometry.within(municipality_geometry)].shape[0]

    return count


@app.cell
def _(charging_stations, cities_utm, municipalities):
    cities_utm["charging_station_count"] = cities_utm["name"].apply(
        lambda name: count_charging_stations_for_municipality(name, municipalities, charging_stations)
    )
    return


@app.cell
def _(cities_utm, pd):
    cities_utm["population"] = (
        cities_utm["population"]
        .str.replace(" ", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype(int)
    )
    return


@app.cell
def _(cities_utm):
    cities_utm
    return


@app.cell
def _(cities_utm, plt):
    cities_filtered = cities_utm[cities_utm["name"] != "Graz"]

    _fig, _ax = plt.subplots(figsize=(12, 8))
    _ax.scatter(
        cities_filtered["population"],
        cities_filtered["charging_station_count"],
        alpha=0.7,
        edgecolors="black"
    )

    top10 = cities_filtered.nlargest(10, "charging_station_count")

    # Add labels for the 10 municipalities with the most charging stations
    for _, row in top10.iterrows():
        _ax.annotate(
            row["name"],
            (row["population"], row["charging_station_count"]),
            fontsize=9,
            fontweight="bold",
            xytext=(5, 5),
            textcoords="offset points"
        )

    _ax.set_xlim(0, cities_filtered["population"].max() * 1.1)
    _ax.set_ylim(0, cities_filtered["charging_station_count"].max() * 1.1)
    _ax.set_xlabel("Population (inhabitants)")
    _ax.set_ylabel("Number of charging stations")
    _ax.set_title("Population vs. Charging Stations by Municipality in Styria [Graz excluded]")

    _ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()
    return


@app.cell
def _(charging_stations_utm):
    charging_stations_utm
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Power-Outlet of the charging stations
    """)
    return


@app.cell
def _(charging_stations_utm):
    slow = charging_stations_utm[charging_stations_utm["Capacity kWh"] <11]
    normal = charging_stations_utm[
        (charging_stations_utm["Capacity kWh"] >= 11) &
        (charging_stations_utm["Capacity kWh"] < 22)
    ]
    fast = charging_stations_utm[
        (charging_stations_utm["Capacity kWh"] >= 22) &
        (charging_stations_utm["Capacity kWh"] < 50)
    ]
    ultra_fast = charging_stations_utm[
        (charging_stations_utm["Capacity kWh"] >= 50) &
        (charging_stations_utm["Capacity kWh"] < 150)
    ]
    HPC = charging_stations_utm[charging_stations_utm["Capacity kWh"] >= 150]
    return fast, normal, slow, ultra_fast


@app.cell
def _(fast, normal, plt, slow, ultra_fast):
    categories = ["Slow", "Medium", "Fast", "Ultra-fast"]
    counts = [
        len(slow),
        len(normal),
        len(fast),
        len(ultra_fast)
    ]

    plt.figure(figsize=(10, 6))

    plt.bar(categories, counts, edgecolor="black")

    plt.xlabel("Power category")
    plt.ylabel("Number of charging stations")
    plt.title("Distribution of Charging Stations by Charging Speed")

    for i, count in enumerate(counts):
        plt.text(i, count, str(count), ha="center", va="bottom")

    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Spatial Analysis
    """)
    return


@app.cell
def _(charging_stations_utm, pd, road_classes, streets_utm):
    # Store distances
    distances = pd.DataFrame(index=charging_stations_utm.index)

    for road_type, classes in road_classes.items():

        # Filter roads by category
        selected_roads = streets_utm[
            streets_utm["fclass"].isin(classes)
        ]

        # Combine all road geometries
        roads_union = selected_roads.geometry.union_all()

        # Calculate distance to nearest road (in km)
        distances[road_type] = (
            charging_stations_utm.geometry.distance(roads_union) / 1000
        )

    distances.head()
    return (distances,)


@app.cell
def _(Line2D, distances, plt, sns):
    _fig, _ax = plt.subplots(figsize=(12, 7))

    sns.boxplot(
        data=distances,
        palette=["skyblue", "lightgreen", "orange"],
        showfliers=True,
        ax=_ax
    )

    _ax.set_title(
        "Distance Between Charging Infrastructure and Road Categories"
    )

    _ax.set_xlabel("Type of Road")
    _ax.set_ylabel("Distance (km)")

    _ax.grid(axis="y", alpha=0.3)

    medians = distances.median()

    legend_elements = [
        Line2D(
            [0], [0],
            color="none",
            label=f"{name} median: {value:.2f} km"
        )
        for name, value in medians.items()
    ]

    _ax.legend(
        handles=legend_elements,
        title="Median Distances",
        loc="upper right"
    )
    plt.tight_layout()
    plt.show()

    print("Median distances to road categories (km):")
    print(distances.median())
    return


@app.cell
def _(charging_stations_utm, np, streets_utm):
    # Select highways
    highways = streets_utm[
        streets_utm["fclass"].isin(["motorway", "motorway_link"])
    ]

    # Combine highway geometries
    highways_union = highways.geometry.union_all()

    # Calculate distance from every charging station to nearest highway
    highway_distances = (
        charging_stations_utm.geometry.distance(highways_union) / 1000
    )

    print(highway_distances.describe())

    # Sort distances
    sorted_distances = np.sort(highway_distances.dropna())

    # Calculate cumulative percentage
    cumulative_percentage = (
        np.arange(1, len(sorted_distances) + 1)
        / len(sorted_distances) * 100
    )
    return cumulative_percentage, sorted_distances


@app.cell
def _(cumulative_percentage, np, plt, sorted_distances):
    _fig, _ax = plt.subplots(figsize=(12, 7))

    _ax.plot(
        sorted_distances,
        cumulative_percentage,
        marker="o",
        markersize=2.5,
        linewidth=1.5,
        color="tab:blue"
    )

    _ax.set_title("Charging Infrastructure Proximity to Highways")
    _ax.set_xlabel("Distance to Highway (Kilometers)")
    _ax.set_ylabel("Stations Within Radius (%)")

    _ax.set_xlim(0, (sorted_distances.max()))
    _ax.set_ylim(0, 95)

    _ax.set_xticks(np.arange(0, 65, 5))
    _ax.set_yticks(np.arange(0, 101, 20))

    _ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Hexagon Grid
    """)
    return


@app.cell
def _(
    CRS,
    Polygon,
    boundary_utm,
    charging_stations_utm,
    gpd,
    h3,
    plt,
    streets_utm,
):
    # Convert Styria boundary to WGS84
    boundary_wgs84 = boundary_utm.to_crs("EPSG:4326")

    # Get boundary geometry
    styria_polygon = boundary_wgs84.geometry.union_all()

    # Convert polygon to GeoJSON format
    styria_geojson = styria_polygon.__geo_interface__

    # Generate H3 cells
    resolution = 7

    hex_ids = h3.geo_to_cells(
        styria_geojson,
        resolution
    )

    print(f"Number of H3 hexagons: {len(hex_ids)}")

    # Create H3 hexagon polygons
    hex_grid = gpd.GeoDataFrame(
        {"hex_id": list(hex_ids)},
        geometry=[
            Polygon(
                [(lng, lat) for lat, lng in h3.cell_to_boundary(hex_id)]
            )
            for hex_id in hex_ids
        ],
        crs="EPSG:4326"
    )

    # Project hexagons to UTM
    hex_grid = hex_grid.to_crs(CRS)

    # Calculate hexagon areas in km²
    hex_grid["area_km2"] = hex_grid.geometry.area / 1_000_000


    # ---------------------------------
    # Assign charging stations to H3 cells
    # ---------------------------------

    charging_wgs84 = charging_stations_utm.to_crs("EPSG:4326")

    charging_wgs84["hex_id"] = charging_wgs84.geometry.apply(
        lambda point: h3.latlng_to_cell(
            point.y,
            point.x,
            resolution
        )
    )

    # Count charging stations per H3 cell
    station_counts = (
        charging_wgs84
        .groupby("hex_id")
        .size()
        .reset_index(name="charging_station_count")
    )

    # Join counts to the H3 grid
    hex_grid_analysis = hex_grid.merge(
        station_counts,
        on="hex_id",
        how="left"
    )

    # Fill cells without charging stations
    hex_grid_analysis["charging_station_count"] = (
        hex_grid_analysis["charging_station_count"]
        .fillna(0)
        .astype(int)
    )

    # Calculate station density
    hex_grid_analysis["stations_per_km2"] = (
        hex_grid_analysis["charging_station_count"]
        / hex_grid_analysis["area_km2"]
    )


    # ---------------------------------
    # Visualisation: Four maps
    # ---------------------------------

    _fig, _axes = plt.subplots(2, 2, figsize=(18, 16))

    # Plot 1: H3 grid outline
    # Plot boundary
    boundary_utm.plot(
        ax=_axes[0, 0],
        facecolor="none",
        edgecolor="black",
        zorder=1
    )

    # Define road classes
    _road_classes = {
        "Highways": ["motorway", "motorway_link"],
        "Trunks": ["trunk", "trunk_link"],
        "Primary roads": ["primary", "primary_link"],
        "Secondary roads": ["secondary", "secondary_link"]
    }

    # Define colours and line widths
    _road_styles = {
        "Highways": {"color": "red", "linewidth": 2},
        "Trunks": {"color": "orange", "linewidth": 1.5},
        "Primary roads": {"color": "gold", "linewidth": 1},
        "Secondary roads": {"color": "grey", "linewidth": 0.5}
    }

    for _road, _types in _road_classes.items():
        streets_utm[streets_utm["fclass"].isin(_types)].plot(
            ax=_axes[0, 0],
            label=_road,
            zorder=3,
            alpha=0.7,
            **_road_styles[_road]
        )

    _axes[0, 0].set_title("Road Network")
    _axes[0, 0].set_axis_off()


    # ---------------------------------
    # Plot 2: Charging station count
    # ---------------------------------

    hex_grid_analysis.plot(
        column="charging_station_count",
        ax=_axes[1, 1],
        cmap="YlOrRd",
        legend=True,
        linewidth=0.2,
        edgecolor="grey"
    )

    boundary_utm.boundary.plot(
        ax=_axes[1, 1],
        color="black",
        linewidth=1
    )

    _axes[1, 1].set_title("Charging Station Count")
    _axes[1, 1].set_axis_off()



    # ---------------------------------
    # Plot 3: Charging station density
    # ---------------------------------

    hex_grid_analysis.plot(
        column="stations_per_km2",
        ax=_axes[1, 0],
        cmap="plasma",
        legend=True,
        linewidth=0.2,
        edgecolor="grey"
    )

    boundary_utm.boundary.plot(
        ax=_axes[1, 0],
        color="black",
        linewidth=1
    )

    _axes[1, 0].set_title("Charging Station Density (per km²)")
    _axes[1, 0].set_axis_off()


    # ---------------------------------
    # Plot 4: H3 grid and Styria boundary only
    # ---------------------------------

    hex_grid.plot(
        ax=_axes[0, 1],
        facecolor="none",
        edgecolor="grey",
        linewidth=0.4,
        zorder=2
    )

    boundary_utm.boundary.plot(
        ax=_axes[0, 1],
        color="black",
        linewidth=1.5,
        zorder=3
    )

    _axes[0, 1].set_title("H3 Hexagonal Grid (Resolution 7)")
    _axes[0, 1].set_axis_off()


    # ---------------------------------
    # Overall figure formatting
    # ---------------------------------

    _fig.suptitle(
        "Spatial Distribution of EV Charging Infrastructure in Styria\n"
        "1 Hexagon ≈ 5.16 km²",
        fontsize=16
    )

    _fig.tight_layout(rect=[0, 0, 1, 0.94])

    _fig
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
