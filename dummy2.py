import streamlit as st
import pandas as pd
from joblib import load
from geopy.geocoders import Nominatim
import openrouteservice
import folium
from streamlit_folium import st_folium
import requests

import base64

def set_background(image_file):
    with open(image_file, "rb") as f:
        encoded_string = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Call this function early in your app
set_background("bg5.jpg")  # Replace with your file name

st.markdown("""
    <style>
    /* Make input fields (text, number, select) transparent */
    .stTextInput > div > div > input,
    .stNumberInput > div > input,
    .stSelectbox > div > div > div {
        background-color: rgba(101, 196, 218, 0) !important;
        color: black !important;
        border: 1px solid #ccc;
    }

    /* Label and text font color */
    label, .stTextInput label, .stNumberInput label, .stSelectbox label {
        color: black !important;
    }

    /* Change header and subheader colors */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: black !important;
    }

    /* Buttons */
    button[kind="primary"] {
        background-color: rgba(255, 255, 255, 0.2) !important;
        color: white !important;
        border: 1px solid white !important;
    }

    button[kind="primary"]:hover {
        background-color: rgba(255, 255, 255, 0.3) !important;
    }
    /* Add semi-transparent white background to st.form container */
    div[data-testid="stForm"] {
        background-color: rgba(255, 255, 255, 0.30);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
            
    /* General info container */
.info-box {
    background-color: rgba(255, 255, 255, 0.40);
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 20px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 0 8px rgba(0,0,0,0.05);
    color: black;
}

/* Route result container */
.route-box {
    background-color: rgba(255, 255, 255, 0.40);
    padding: 15px;
    margin-bottom: 12px;
    border-radius: 10px;
    border: 1px solid #ccc;
    color: black;
}

/* Highlight for best route */
.best-route {
    border: 2px solid #00cc99;
    background-color: rgba(0, 255, 204, 0.30);
}

.best-route-highlight {
    border: 2px solid #28a745;
    background-color: rgba(255, 255, 255, 0.60);
    color: #155724;
}

    </style>
""", unsafe_allow_html=True)





# Load model and encoder
try:
    model = load("random_forest_model.pkl")
    encode_dict = load("encode_dict.pkl")
except FileNotFoundError:
    st.error("Model or encoder file not found. Please ensure 'random_forest_model.pkl' and 'encode_dict.pkl' are in the correct path.")
    st.stop()

import requests

def get_weather_info(lat, lon, api_key):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        response = requests.get(url)
        data = response.json()

        weather_main = data['weather'][0]['main'].lower()
        temperature = data['main']['temp']
        wind_speed = data['wind']['speed']

        # Map OpenWeatherMap condition to your categories
        if weather_main in ['rain', 'drizzle', 'thunderstorm']:
            weather= 'rainy'
            if weather_main == "rain":
                weather_intensity="moderate"
            elif weather_main == "drizzle":
                weather_intensity="low"
            elif weather_main == "thunderstorm":
                weather_intensity="high"

        elif weather_main in ['snow', 'mist', 'fog', 'haze', 'smoke']:
            weather= 'winter'
            if weather_main in [ "snow","fog"]:
                weather_intensity="high"
            elif weather_main == "mist":
                weather_intensity="low"
            elif weather_main in ["haze","smoke"]:
                weather_intensity="high"

        else:
            weather = 'sunny'
            if temperature > 35 :
                weather_intensity="high"
            elif temperature > 25 and temperature<=35: 
                weather_intensity="moderate"
            else:
                weather_intensity="low"
        
        return weather,weather_intensity, temperature, wind_speed

    except Exception as e:
        st.warning(f"Failed to fetch weather info: {e}")
        return 'sunny', 30, 10  # default fallback




# ORS and Geolocation
ors_client = openrouteservice.Client(key='5b3ce3597851110001cf62484ebe407adc8b4fb1b4b26a61bce969e1')  # Replace with your key
geolocator = Nominatim(user_agent="geoapi")

# App Title
st.title("CO2 Emission Predictor for Logistics Routes")

# Estimate fuel usage function
def estimate_fuel_usage(distance_km, vehicle_type, fuel_type, cargo_weight_kg, traffic_intensity):
    mileage_table = {
        'mini tempo': {'petrol': 12, 'diesel': 15},
        'open cargo': {'petrol': 8, 'diesel': 10},
        'closed cargo': {'petrol': 7, 'diesel': 9},
        'raw cargo': {'petrol': 5, 'diesel': 7},
        'liquid cargo': {'petrol': 4, 'diesel': 6},
    }
    base_mileage = mileage_table[vehicle_type][fuel_type]
    load_factor = 1 + (cargo_weight_kg / 10000)
    traffic_factor = {'low': 1.0, 'moderate': 1.1, 'high': 1.25}[traffic_intensity]
    adjusted_factor = load_factor * traffic_factor
    return round((distance_km / base_mileage) * adjusted_factor, 2)


# Form
with st.form("input_form"):
    st.subheader("Route Details")
    col1, col2 = st.columns(2)
    with col1:
        source = st.text_input("Source Location (e.g., Thane)")
    with col2:
        destination = st.text_input("Destination Location (e.g., Vashi)")

    st.subheader("Vehicle & Environment Inputs")
    col3, col4 = st.columns(2)
    with col3:
        vehicle_type = st.selectbox("Vehicle Type", ['mini tempo', 'open cargo', 'closed cargo', 'raw cargo', 'liquid cargo'])
        fuel_type = st.selectbox("Fuel Type", ['petrol', 'diesel'])
        #road_type = st.selectbox("Road Type", ['highway', 'urban', 'rural'])
    with col4:
        #weather = st.selectbox("Weather", ['sunny', 'rainy', 'winter'])
        #weather_intensity = st.selectbox("Weather Intensity", ['low', 'moderate', 'high'])
        road_type = st.selectbox("Road Type", ['highway', 'urban', 'rural'])
        cargo_weight_kg = st.number_input("Cargo Weight (kg)", 1.0, 50000.0, 1000.0)

    
    submitted = st.form_submit_button("Predict CO2 Emissions")

# Handle form submit
if submitted:
    if not source or not destination:
        st.warning(" Please enter both source and destination.")
    else:
        try:
            source_loc = geolocator.geocode(source)
            dest_loc = geolocator.geocode(destination)

            if not source_loc or not dest_loc:
                st.error(" Could not find coordinates for one or both locations.")
            else:
                coords = [(source_loc.longitude, source_loc.latitude), (dest_loc.longitude, dest_loc.latitude)]

                try:
                    # Avoid exceeding 100km limit
                    distance_check = ors_client.directions(
                        coordinates=coords,
                        profile='driving-car',
                        format='geojson'
                    )
                    total_distance = distance_check['features'][0]['properties']['segments'][0]['distance']

                    if total_distance > 100000:
                        st.error(" Route distance exceeds 100 km limit for alternative routes.")
                    else:
                        # Get main + alternative routes
                        routes = ors_client.directions(
                            coordinates=coords,
                            profile='driving-car',
                            format='geojson',
                            alternative_routes={"share_factor": 0.5, "target_count": 2}
                        )

                        m = folium.Map(location=[source_loc.latitude, source_loc.longitude], zoom_start=6)
                        colors = ['blue', 'red', 'green','yellow']
                        results = []

                        for idx, route in enumerate(routes['features']):
                            segment = route['properties']['segments'][0]
                            distance_km = round(segment['distance'] / 1000, 2)
                            duration_min = round(segment['duration'] / 60, 2)

                            speed_kmh = distance_km / (duration_min / 60)
                            traffic_intensity = (
                                "low" if speed_kmh > 40 else
                                "moderate" if speed_kmh > 20 else
                                "high"
                            )

                            fuel_usage_liters = estimate_fuel_usage(
                                distance_km, vehicle_type, fuel_type, cargo_weight_kg, traffic_intensity
                            )
                            w_api_key = "a82175121cc64418225d9e29f81f6a1b"
                            weather,weather_intensity, temperature_celsius, wind_speed_kmph = get_weather_info(source_loc.latitude, source_loc.longitude, w_api_key)
                            print(weather,weather_intensity, temperature_celsius, wind_speed_kmph)
                            input_data = pd.DataFrame([{
                                'total_distance_km': distance_km,
                                'vehicle_type': encode_dict['vehicle_type'].tolist().index(vehicle_type),
                                'fuel_type': encode_dict['fuel_type'].tolist().index(fuel_type),
                                'traffic_intensity': encode_dict['traffic_intensity'].tolist().index(traffic_intensity),
                                'weather': encode_dict['weather'].tolist().index(weather),
                                'weather_intensity': encode_dict['weather_intensity'].tolist().index(weather_intensity),
                                'temperature_celsius': temperature_celsius,
                                'wind_speed_kmph': wind_speed_kmph,
                                'cargo_weight_kg': cargo_weight_kg,
                                'fuel_usage_liters': fuel_usage_liters,
                                'road_type': encode_dict['road_type'].tolist().index(road_type)
                            }])

                            co2_prediction = model.predict(input_data)[0]

                            results.append({
                                'Route': f"Route {idx + 1}",
                                'Distance (km)': distance_km,
                                'Duration (min)': duration_min,
                                'Traffic': traffic_intensity,
                                'Fuel Used (L)': fuel_usage_liters,
                                'CO₂ Emission (kg)': round(co2_prediction, 2)
                            })

                            coordinates = route['geometry']['coordinates'] 
                            latlon_coords = [(coord[1], coord[0]) for coord in coordinates]
                            folium.PolyLine(
                                    locations=latlon_coords,
                                    color=colors[idx % len(colors)],
                                    weight=5,
                                    opacity=0.7,
                                    tooltip=f"Route {idx + 1}"
                                ).add_to(m)
                                                            

                    

                        folium.LayerControl().add_to(m)
                        legend_items = ""
                        for idx, result in enumerate(results):
                            color = colors[idx % len(colors)]
                            legend_items += f'<i style="background:{color};color:{color};">____</i> {result["Route"]}<br>'

                        legend_html = f"""
                        <div style="
                            position: fixed; 
                            bottom: 50px; left: 50px; width: 180px; height: auto; 
                            background-color: white; z-index:9999; font-size:14px;
                            border:2px solid grey; padding: 10px;">
                        <b> Route Legend</b><br>
                        {legend_items}
                        </div>
                        """

                        m.get_root().html.add_child(folium.Element(legend_html))
                        # Find the route with lowest CO₂ emission
                        best_route_idx = min(range(len(results)), key=lambda i: results[i]['CO₂ Emission (kg)'])
                        best_route = results[best_route_idx]
                        
                        st.session_state['results'] = results
                        st.session_state['map'] = m
                        st.session_state['route'] = best_route
                        st.session_state["weather_data"] = (weather,weather_intensity, temperature_celsius, wind_speed_kmph)




                except Exception as e:
                    st.error(f"Route calculation error: {e}")

        except Exception as e:
            st.error(f"Location lookup error: {e}")


# if 'weather_data' in st.session_state:
#      st.subheader("Current weather status")
#      st.write("Following data is provided to the model:")
#      st.write(f"current weather is {st.session_state["weather_data"][0]} & current temperature is {st.session_state["weather_data"][2]} & current wind speed is {st.session_state["weather_data"][3]}")


# # Display results if they exist
# if 'results' in st.session_state and st.session_state['results']:
#     st.subheader("Route Comparison")
#     st.dataframe(pd.DataFrame(st.session_state['results']))
    
    

# if 'map' in st.session_state:
#     st.subheader("Route Map")
#     st_folium(st.session_state['map'], width=700, height=500)

# if 'route' in st.session_state:
#      st.subheader("Environment Friendly Route")
#      st.write(f"Best route is: {st.session_state['route']["Route"]} which will emits {st.session_state['route']["CO₂ Emission (kg)"]} KG of CO₂ Emission (kg)")

# Weather Data Box
if 'weather_data' in st.session_state:
    weather, weather_intensity, temp, wind = st.session_state["weather_data"]

    st.markdown(f"""
    <div class="info-box">
        <h4>🌦️ Current Weather Status</h4>
        <p>Following data is provided to the model:</p>
        <ul>
            <li>🌤️ Weather: <b>{weather}</b></li>
            <li>🌡️ Temperature: <b>{temp} °C</b></li>
            <li>💨 Wind Speed: <b>{wind} km/h</b></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


# Route Results Box
if 'results' in st.session_state and st.session_state['results']:
    st.markdown("<div class='info-box'><h4>🛣️ Route Comparison</h4>", unsafe_allow_html=True)

    for result in st.session_state['results']:
        is_best = result['Route'] == st.session_state['route']['Route']
        box_class = "route-box best-route" if is_best else "route-box"

        st.markdown(f"""
        <div class="{box_class}">
            <b>{result['Route']}</b><br>
            Distance: {result['Distance (km)']} km<br>
            Duration: {result['Duration (min)']} min<br>
            Traffic: {result['Traffic']}<br>
            Fuel Used: {result['Fuel Used (L)']} L<br>
            CO2 Emission: {result['CO₂ Emission (kg)']} kg
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# Map Box
if 'map' in st.session_state:
    st.markdown("<div class='info-box'><h4>🗺️ Route Map</h4>", unsafe_allow_html=True)
    st_folium(st.session_state['map'], width=700, height=500)
    st.markdown("</div>", unsafe_allow_html=True)

# Best Route Box
if 'route' in st.session_state:
    st.markdown(f"""
    <div class="info-box best-route-highlight">
        <h4> Environment Friendly Route</h4>
        <p><b>{st.session_state['route']["Route"]}</b> emits the least CO₂:
        <b>{st.session_state['route']["CO₂ Emission (kg)"]} kg</b></p>
    </div>
    """, unsafe_allow_html=True)
