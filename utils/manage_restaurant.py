import os
import json
from models.restaurant import Restaurant, RestaurantType
import discord
from discord import app_commands

all_restaurants = []
def get_all_restaurants():
    global all_restaurants
    """
    Get all restaurants from the database.
    """

    if all_restaurants:
        return all_restaurants

    path = os.path.join(os.path.dirname(__file__), "..\\data")
    if not os.path.exists(path):
        os.makedirs(path)

    if not os.path.exists("data/restaurants.json"):
        return {}

    with open("data/restaurants.json", "r") as file:
        restaurants = json.load(file)

    all_restaurants = restaurants

    return restaurants

def get_restaurant_by_id(restaurant_id):
    """
    Get a restaurant by its ID from the database.
    """

    restaurants = get_all_restaurants()

    for restaurant in restaurants:
        if restaurant["id"] == restaurant_id:
            return restaurant

    return None

def save_restaurant(restaurant: Restaurant) -> bool:
    """
    Save a restaurant to the database.
    """

    all_restaurants = get_all_restaurants()
    all_restaurants[restaurant.name] = restaurant.to_dict()

    with open("data/restaurants.json", "w") as file:
        json.dump(all_restaurants, file, indent=4)
        load_all_restaurants()

    return True

restaurant_objects = {}
def load_all_restaurants():
    global restaurant_objects
    restaurant_objects = {}
    restaurants = get_all_restaurants()
    for restaurant_name, restaurant_data in restaurants.items():
        restaurant_data["permissions"] = {int(k): v for k, v in restaurant_data.get("permissions", {}).items()}

        restaurant_objects[restaurant_name] = Restaurant(**restaurant_data)

    return restaurant_objects

def get_restaurant_object(restaurant_name):
    """
    Get a restaurant object by its name.
    """

    global restaurant_objects
    if not restaurant_objects:
        restaurant_objects = load_all_restaurants()

    return restaurant_objects.get(restaurant_name, None)

def is_existing_restaurant(restaurant_name):
    """
    Check if a restaurant exists in the database.
    """

    restaurants = get_all_restaurants()
    if restaurant_name in restaurants:
        return True

    return False

def delete_restaurant(restaurant_name):
    """
    Delete a restaurant from the database.
    """

    restaurants = get_all_restaurants()
    if restaurant_name in restaurants:
        del restaurants[restaurant_name]

        with open("data/restaurants.json", "w") as file:
            json.dump(restaurants, file, indent=4)

        return True

    return False

class RestaurantTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> "Restaurant":
        return value

    async def autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        restaurants = get_all_restaurants()
        return [
            app_commands.Choice(name=restaurant["name"], value=restaurant["name"])
            for restaurant in restaurants.values()
            if current.lower() in restaurant["name"].lower()
        ][:25]

# TYPE RESTAURANT
restaurant_types = []
def get_all_restaurant_types():
    """
    Get all restaurant types from the database.
    """

    path = os.path.join(os.path.dirname(__file__), "..\\data")
    if not os.path.exists(path):
        os.makedirs(path)

    if not os.path.exists("data/restaurant_types.json"):
        return []

    with open("data/restaurant_types.json", "r") as file:
        restaurant_types = json.load(file)

    return restaurant_types

def save_restaurant_type(restaurant_type: RestaurantType) -> bool:
    """
    Save a restaurant type to the database.
    """

    all_restaurant_types = get_all_restaurant_types()
    all_restaurant_types.append(restaurant_type.__str__())

    with open("data/restaurant_types.json", "w") as file:
        json.dump(all_restaurant_types, file, indent=4)

    return True

def is_existing_restaurant_type(restaurant_type_name):
    """
    Check if a restaurant type exists in the database.
    """

    restaurant_types = get_all_restaurant_types()
    for restaurant_type in restaurant_types:
        if restaurant_type == restaurant_type_name:
            return True
    return False

def delete_restaurant_type(restaurant_type_name):
    """
    Delete a restaurant type from the database.
    """

    restaurant_types = get_all_restaurant_types()
    if restaurant_type_name in restaurant_types:
        restaurant_types.remove(restaurant_type_name)

        with open("data/restaurant_types.json", "w") as file:
            json.dump(restaurant_types, file, indent=4)

        return True

    return False

class RestaurantTypeTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> RestaurantType:
        if is_existing_restaurant_type(value):
            return RestaurantType(value)

        return None

    async def autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        restaurant_types = get_all_restaurant_types()
        return [
            app_commands.Choice(name=restaurant_type, value=restaurant_type)
            for restaurant_type in restaurant_types
            if current.lower() in restaurant_type.lower()
        ][:25]