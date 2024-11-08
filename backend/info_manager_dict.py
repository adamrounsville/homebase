import dataclasses
import uuid

@dataclasses.dataclass
class Place:
    name: str
    ID: str
    latitude: float
    longitude: float

@dataclasses.dataclass
class UserInfo:
    home: tuple[float, float]
    places: dict[str, list[Place]]

class InfoManagerDict:
    def __init__(self):
        self.data = dict()

    def add_user(self, latitude: float, longitude: float):
        user_id = str(uuid.uuid4())
        info = UserInfo(home=(latitude, longitude), places=dict())
        self.data[user_id] = info
        return user_id

    def get_user(self, user_id: str):
        return self.data[user_id]
    
    def add_place(self, activity_group: str, user_id: str, name: str, id: str, latitude: float, longitude: float):
        self.data[user_id].places[activity_group].append(Place(name, id, latitude, longitude))

    def get_places(self, user_id: str):
        return [place for places in self.data[user_id].places.values() for place in places]
    
    def delete_place(self, user_id: str, activity_group: str, id: str):
        if user_id in self.data and activity_group in self.data[user_id].places:
            self.data[user_id].places[activity_group] = [
                place for place in self.data[user_id].places[activity_group] if place.ID != id
            ]

    def add_activity_group(self, user_id: str, activity_group: str):
        self.data[user_id].places[activity_group] = []

    def get_activity_group(self, user_id: str, activity_group: str):
        return self.data[user_id].places[activity_group]
    
    def delete_activity_group(self, user_id: str, activity_group: str):
        del self.data[user_id].places[activity_group]

    def activity_group_exists(self, user_id: str, activity_group: str):
        return user_id in self.data and activity_group in self.data[user_id].places

    def get_all_activity_groups(self, user_id: str):
    """
    Returns all activity groups and their places for a given user.
    Returns a list of tuples containing (group_name, places_list)
    """
    if user_id not in self.data:
        raise KeyError("User not found")
    
    return [
        {
            "name": group_name,
            "places": places
        }
        for group_name, places in self.data[user_id].places.items()
    ]
