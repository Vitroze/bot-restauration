import discord
from discord import app_commands

class Restaurant:
    def __init__(self, name:str, description:str, type:str, location:str, reservations:list = [], permissions:dict = {}, menu:list = []):
        self.name = name
        self.description = description
        self.type = type
        self.location = location
        self.reservations = reservations or []  # List of reservations for this restaurant
        self.permissions = permissions or {}  # Dictionary to store user permissions for this restaurant
        self.menu = menu or []  # List of menu items for this restaurant

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "location": self.location,
            "reservations": self.reservations,
            "permissions": self.permissions,
            "menu": self.menu
        }

    def __str__(self):
        return f"Restaurant(name={self.name}, description={self.description}, type={self.type}, location={self.location})"

    def add_permission(self, role_id: int, permission: str):
        if role_id not in self.permissions:
            self.permissions[role_id] = []
        if permission not in self.permissions[role_id]:
            self.permissions[role_id].append(permission)

    def remove_permission(self, role_id: int, permission: str):
        if role_id in self.permissions and permission in self.permissions[role_id]:
            self.permissions[role_id].remove(permission)
            if not self.permissions[role_id]:  # Remove the role if no permissions left
                del self.permissions[role_id]

    def has_permission(self, role_id: int, permission: str) -> bool:
        return role_id in self.permissions and permission in self.permissions[role_id]

class RestaurantType:
    def __init__(self, name:str):
        self.name = name

    def to_name(self):
        return self.name

    def __str__(self):
        return self.name