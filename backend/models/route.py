from pydantic import BaseModel
from typing import List

class RouteStep(BaseModel):
    distance_meters: int
    duration_seconds: int
    start_location: tuple[float, float]
    end_location: tuple[float, float]

class Route(BaseModel):
    total_distance: int
    total_duration: int
    steps: List[RouteStep]
