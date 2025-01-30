import requests
import folium
import pandas as pd
from django.shortcuts import render
from scipy.spatial import cKDTree
from geopy.distance import geodesic
from .models import FuelStation
from .forms import RouteForm
from polyline import decode
import numpy as np
from django.conf import settings 


# Getting the route from Google Directions API

def get_route(origin, destination):
    api_key = settings.GOOGLE_MAPS_API_KEY  
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={api_key}"
    response = requests.get(url)
    data = response.json()

    if data["status"] == "OK":
        route = []
        for leg in data["routes"][0]["legs"]:
            for step in leg["steps"]:
                points = step["polyline"]["points"]
                decoded_points = decode(points)  
                route.extend(decoded_points)
        return route
    else:
        print("Error fetching route:", data["status"])
        return None


# Creating spatial index for fuel station lookup

def create_spatial_index(fuel_data):
    fuel_coords = fuel_data[["latitude", "longitude"]].values
    return cKDTree(fuel_coords)


# Finding best fuel station

def find_best_fuel_station(location, fuel_data, spatial_index, max_distance=20, distance_weight=0.1):
    distances, indices = spatial_index.query([location], k=5, distance_upper_bound=max_distance)
    valid_indices = indices[0][indices[0] < len(fuel_data)]

    if len(valid_indices) == 0:
        return None

    scores = []
    for i, index in enumerate(valid_indices):
        station = fuel_data.iloc[index]
        price = station["price"]
        distance = distances[0][i]
        score = price + distance * distance_weight
        scores.append((score, station))

    best_station = min(scores, key=lambda x: x[0])[1]
    return ((best_station["latitude"], best_station["longitude"]), best_station["price"])



# Finding fuel stops along the route

def find_fuel_stops(route, fuel_data, spatial_index, segment_length=450, max_search_radius=100):
    fuel_stops = []
    total_distance = 0
    total_fuel_cost = 0
    miles_per_gallon = 10

    for i in range(1, len(route)):
        prev_point = route[i - 1]
        curr_point = route[i]
        segment_distance = geodesic(prev_point, curr_point).miles
        total_distance += segment_distance

        if total_distance >= segment_length:
            best_stop = None
            for radius in [20, 50, max_search_radius]:
                best_stop = find_best_fuel_station(curr_point, fuel_data, spatial_index, max_distance=radius)
                if best_stop:
                    break

            if best_stop:
                station_coords, price_per_gallon = best_stop
                fuel_stops.append((station_coords, price_per_gallon))
                fuel_consumed = total_distance / miles_per_gallon
                total_fuel_cost += fuel_consumed * price_per_gallon
                total_distance = 0  
            else:
                print(f"No fuel station found near {curr_point}. Exiting.")
                break

    return fuel_stops, total_fuel_cost


# Plotting route & fuel stops using Folium

def plot_route_with_stops(route, fuel_stops, origin, destination):
    m = folium.Map(location=route[0], zoom_start=6)

    folium.PolyLine(route, color="blue", weight=2.5, opacity=1).add_to(m)

    folium.Marker(location=route[0], popup=f"Origin: {origin}", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(location=route[-1], popup=f"Destination: {destination}", icon=folium.Icon(color="blue")).add_to(m)

    for i, stop in enumerate(fuel_stops, start=1):
        lat, lon = stop[0]
        price_per_gallon = stop[1]

        station = FuelStation.objects.filter(latitude=lat, longitude=lon).first()
        popup_text = f"<b>Stop {i}</b><br>Price per Gallon: ${price_per_gallon:.2f}"
        if station:
            popup_text = (f"<b>Stop {i}:</b><br>{station.name}, {station.city}, {station.state}<br>"
                          f"<b>Price per Gallon:</b> ${price_per_gallon:.2f}")
        folium.Marker(location=(lat, lon), popup=popup_text, icon=folium.Icon(color="red")).add_to(m)

    return m._repr_html_()  


def home(request):
    form = RouteForm()
    map_html = None
    total_fuel_cost = 0
    fuel_stops = []

    if request.method == "POST":
        form = RouteForm(request.POST)
        if form.is_valid():
            origin = form.cleaned_data["origin"]
            destination = form.cleaned_data["destination"]

            route = get_route(origin, destination)
            if route:
                fuel_stations_df = pd.DataFrame(list(FuelStation.objects.all().values()))
                spatial_index = create_spatial_index(fuel_stations_df)

                fuel_stops_coords, total_fuel_cost = find_fuel_stops(route, fuel_stations_df, spatial_index)

                for stop_coords, price_per_gallon in fuel_stops_coords:
                    station = FuelStation.objects.filter(latitude=stop_coords[0], longitude=stop_coords[1]).first()
                    if station:
                        fuel_stops.append({
                            "name": station.name,
                            "address": station.address,
                            "city": station.city,
                            "state": station.state,
                            "price_per_gallon": price_per_gallon,
                        })

                map_html = plot_route_with_stops(route, fuel_stops_coords, origin, destination)

    return render(request, "spotter_lab/home.html", {
        "form": form,
        "map_html": map_html,
        "fuel_stops": fuel_stops,
        "total_fuel_cost": total_fuel_cost,
    })
