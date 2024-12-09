from typing import Union, Annotated
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
import googlemaps
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
import requests

from models.place import Place
from models.latlon import LatLon
from models.route import Route
from info_manager_dict import InfoManagerDict

CORS_CONFIG = {
    "allow_origins": ["*"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

load_dotenv()

db = InfoManagerDict()
gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

app = FastAPI()
app.add_middleware(CORSMiddleware, **CORS_CONFIG)

@app.post("/place")
def add_place(user_id: Annotated[str, Body()], place_name: Annotated[str, Body()], activity_group: Annotated[str, Body()]):
    """
    Takes in a user ID, location name, and activity group from the frontend, adds a Place made with information from
    the Google Places API to the user's places, and returns the Place object.
    """
    try:
        user = db.get_user(user_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not db.activity_group_exists(user_id, activity_group):
        raise HTTPException(status_code=404, detail="Activity group not found")

    # Bias results within 100km of the user's homebase
    place_result = gmaps.places(place_name, user.home, radius=100000)
    if not place_result['results']:
        raise HTTPException(status_code=404, detail="Place not found")

    place_info = place_result['results'][0]

    place_id = place_info['place_id']
    name = place_info['name']
    location = place_info['geometry']['location']
    latitude = location['lat']
    longitude = location['lng']

    db.add_place(activity_group, user_id, name, place_id, latitude, longitude)

    return { "place": Place(name=name, ID=place_id, latitude=latitude, longitude=longitude) }

@app.get("/place")
def get_place(user_id: str, place_name: str):
    """
    Takes in a user ID and a location name from the frontend, returns a Place object with information from the user's places
    """
    if user_id not in db.data:
        raise HTTPException(status_code=404, detail="User not found")

    user_places = db.get_places(user_id)

    place = next((p for p in user_places if p.name.lower() == place_name.lower()), None)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found for this user")

    return { "place": Place(name=place.name, ID=place.ID, latitude=place.latitude, longitude=place.longitude) }

@app.delete("/place")
def delete_place(user_id: Annotated[str, Body()], activity_group: Annotated[str, Body()], place_id: Annotated[str, Body()]):
    """
    Takes in a user ID, location name, and activity group from the frontend, deletes the place from the user's places
    """
    if user_id not in db.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not db.activity_group_exists(user_id, activity_group):
        raise HTTPException(status_code=404, detail="Activity group not found")
    
    db.delete_place(user_id, activity_group, place_id)

    return { "message" : "success" }

@app.post("/activity-group")
def add_activity_group(user_id: Annotated[str, Body()], activity_group: Annotated[str, Body()]):
    """
    Takes in a user ID and an activity group name from the frontend, adds the activity group to the user's places
    """
    if user_id not in db.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.add_activity_group(user_id, activity_group)

    return { "message" : "success" }

@app.get("/activity-group")
def get_activity_group(user_id: Annotated[str, Body()], activity_group: Annotated[str, Body()]):
    """
    Takes in a user ID and an activity group name from the frontend, returns the activity group from the user's places
    """
    if user_id not in db.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    places = db.get_activity_group(user_id, activity_group)

    return { "places" : [
        Place(
            name=place.name,
            ID=place.ID,
            latitude=place.latitude,
            longitude=place.longitude
        )
        for place in places
    ] }

@app.delete("/activity-group")
def delete_activity_group(user_id: Annotated[str, Body()], activity_group: Annotated[str, Body()]):
    """
    Takes in a user ID and an activity group name from the frontend, deletes the activity group from the user's places
    """
    if user_id not in db.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete_activity_group(user_id, activity_group)

    return { "message" : "success" }

@app.post("/homebase")
def set_homebase(address: Annotated[str, Body()]):
    """
    Takes in a address from the frontend, sets the information for use in the backend, and returns the UUID associated with 
    the user.
    """
    geocode_result = gmaps.geocode(address)

    lat = geocode_result[0]['geometry']['location']['lat']
    lng = geocode_result[0]['geometry']['location']['lng']
    
    uuid = db.add_user(lat, lng)

    return { "uuid": uuid }

@app.get("/route")
def get_route(user_id: Annotated[str, Body()], daily_plan_id: Annotated[str, Body()]):
    """
    Takes in a daily plan ID from the frontend, returns a Route made from the cooresponding places using the Google Routes API
    """

    places = db.get_daily_plan(user_id, daily_plan_id)

    #Google API Call

    return { "message" : f"Loaded places for '{daily_plan_id}'."}

@app.get("/users")
def get_users():
    """
    Returns a list of all users in the database with their homebase locations
    """
    users = []
    for user_id, user_info in db.data.items():
        users.append({
            "user_id": user_id,
            "homebase": {
                "latitude": user_info.home[0],
                "longitude": user_info.home[1]
            }
        })
    
    return { "users": users }

@app.get("/data/{uuid}")
def get_user_data():
    """
    Returns a list of all users in the database with their homebase locations
    """
    users = []
    for user_id, user_info in db.data.items():
        users.append({
            "user_id": user_id,
            "homebase": {
                "latitude": user_info.home[0],
                "longitude": user_info.home[1]
            }
        })
    
    return { "users": users }

@app.put("/place/daily-plan")
def add_place_to_daily_plan(user_id: Annotated[str, Body()], 
                            place_id: Annotated[str, Body()], 
                            daily_plan_id: Annotated[str, Body()]):
    """
    Takes in a user ID, place ID, and daily plan ID from the frontend, adds the place to the daily plan.
    """
    if user_id not in db.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.add_to_daily_plan(user_id, daily_plan_id, place_id)

    return { "message" : "success" }

@app.delete("/place/daily-plan")
def remove_place_from_daily_plan(user_id: Annotated[str, Body()], 
                                 place_id: Annotated[str, Body()],
                                 daily_plan_id: Annotated[str, Body()]):
    """
    Takes in a user ID, and place ID from the frontend, removes the place from it's the daily plan.
    """
    if user_id not in db.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.remove_from_daily_plan(user_id, daily_plan_id, place_id)

    return { "message" : "success" }

@app.get("/daily-plan")
def get_daily_plan(user_id: Annotated[str, Body()], daily_plan_id: Annotated[str, Body()]):
    """
    Takes in a user ID and an daily plan ID from the frontend, returns the daily plan from the user's places.
    """
    if user_id not in db.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    places = db.get_daily_plan(user_id, daily_plan_id)

    return { "places" : [
        Place(
            name=place.name,
            ID=place.ID,
            latitude=place.latitude,
            longitude=place.longitude
        )
        for place in places
    ] }

@app.get("/daily-plan/all")
def get_all_daily_plan_ids(user_id: Annotated[str, Body()]):
    """
    Takes in a user id from the frontend, returns a list of all the daily plans the user has.
    """
    if user_id not in db.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    dp_list = db.get_daily_plan_list(user_id)

    return { "daily_plans" : dp_list }

@app.delete("/daily-plan")
def delete_daily_plan(user_id: Annotated[str, Body()], daily_plan_id: Annotated[str, Body()]):
    """
    Takes in a user id and daily plan id front the frontend, deletes the associated daily plan
    """
    if user_id not in db.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete_daily_plan(user_id, daily_plan_id)

    return { "message" : "success" }

@app.post("/daily-plan")
def add_daily_plan(user_id: Annotated[str, Body()], daily_plan_id: Annotated[str, Body()]):
    """
    Takes in a user id and daily plan id front the frontend, creates a daily plan with that id
    """
    if user_id not in db.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.create_daily_plan(user_id, daily_plan_id)

    return { "message" : "success" }

@app.post("/optimize-routes")
async def optimize_routes(user_id: Annotated[str, Body()]):
    """
    Takes in a user ID and optimizes routes for all trips in their vacation plans
    using Google Maps Compute Routes API.
    """
    try:
        # Get all daily plans for the user
        daily_plans = db.get_daily_plan_list(user_id)
        
        optimized_routes = []
        
        for plan_id in daily_plans:
            places = db.get_daily_plan(user_id, plan_id)
            
            if not places or len(places) < 2:
                continue
                
            # Prepare request for Google Maps API
            origin = {
                "location": {
                    "latLng": {
                        "latitude": places[0].latitude,
                        "longitude": places[0].longitude
                    }
                }
            }
            
            destination = {
                "location": {
                    "latLng": {
                        "latitude": places[-1].latitude,
                        "longitude": places[-1].longitude
                    }
                }
            }
            
            intermediates = []
            for place in places[1:-1]:
                intermediates.append({
                    "location": {
                        "latLng": {
                            "latitude": place.latitude,
                            "longitude": place.longitude
                        }
                    }
                })
            
            request_body = {
                "origin": origin,
                "destination": destination,
                "intermediates": intermediates,
                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_AWARE",
                "computeAlternativeRoutes": False,
                "optimizeWaypointOrder": True
            }
            
            # Make request to Google Maps API
            url = "https://routes.googleapis.com/directions/v2:computeRoutes"
            headers = {
                "X-Goog-Api-Key": os.getenv("GOOGLE_MAPS_API_KEY"),
                "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.optimizedIntermediateWaypointIndex"
            }
            
            response = requests.post(url, json=request_body, headers=headers)
            
            if response.status_code == 200:
                route_data = response.json()
                optimized_routes.append({
                    "plan_id": plan_id,
                    "route_data": route_data
                })
            
        return {"optimized_routes": optimized_routes}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
