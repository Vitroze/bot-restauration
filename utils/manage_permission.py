import functools
import inspect
from typing import Callable

import discord

from .manage_restaurant import get_all_restaurants, get_restaurant_object


def has_restaurant_permission(user, restaurant, permission: str) -> bool:
    """Vérifie qu'un membre possède `permission` sur un restaurant.

    Les administrateurs Discord sont toujours acceptés. Sinon, la permission
    doit être accordée à un rôle du membre ou directement à l'utilisateur.
    `restaurant` accepte un dict sérialisé ou un objet Restaurant.
    """
    if _is_discord_admin(user):
        return True
    permissions = _extract_permissions(restaurant)
    if not permissions:
        return False
    if _is_granted(permissions, getattr(user, "id", None), permission):
        return True
    return any(
        _is_granted(permissions, role.id, permission) for role in getattr(user, "roles", None) or []
    )


def _is_discord_admin(user) -> bool:
    guild_permissions = getattr(user, "guild_permissions", None)
    return guild_permissions is not None and guild_permissions.administrator


def _extract_permissions(restaurant) -> dict:
    if isinstance(restaurant, dict):
        return restaurant.get("permissions") or {}
    return getattr(restaurant, "permissions", None) or {}


def _is_granted(permissions: dict, key, permission: str) -> bool:
    if key is None:
        return False
    granted = permissions.get(key, permissions.get(str(key)))
    return bool(granted) and permission in granted


async def ensure_ui_permission(
    interaction: discord.Interaction, restaurant_name: str | None, permission: str
) -> bool:
    """Vérifie une permission pour un callback de vue/UI.

    Envoie un message éphémère et retourne False si l'accès est refusé.
    Si le restaurant est introuvable, retourne True : le callback affichera
    son propre message d'erreur.
    """
    restaurant = get_all_restaurants().get(restaurant_name) if restaurant_name else None
    if restaurant is None or has_restaurant_permission(interaction.user, restaurant, permission):
        return True
    await interaction.response.send_message(
        f"Vous n'avez pas la permission `{permission}` pour le restaurant " f"`{restaurant_name}`.",
        ephemeral=True,
    )
    return False


def check_ui_permission(permission: str, restaurant_attr: str = "restaurant_name") -> Callable:
    """Décorateur de callback de vue : vérifie `permission` sur le restaurant visé.

    `restaurant_attr` désigne l'attribut de la vue portant le nom du restaurant
    (« restaurant_name » par défaut, « selected » pour ConfigRestaurantView).
    """

    def decorator(callback):
        @functools.wraps(callback)
        async def wrapper(view, interaction, *args, **kwargs):
            restaurant_name = getattr(view, restaurant_attr, None)
            if not await ensure_ui_permission(interaction, restaurant_name, permission):
                return
            return await callback(view, interaction, *args, **kwargs)

        return wrapper

    return decorator


def check_permission(
    param: str, model: Callable, callback_check: Callable, permission: str
) -> Callable:
    async def predicate(interaction: discord.Interaction) -> bool:
        any_variable = getattr(interaction.namespace, param, None)
        object = model(any_variable)
        if inspect.isawaitable(object):
            object = await object

        if object is None:
            await interaction.response.send_message(
                f"Aucun objet trouvé pour la valeur '{any_variable}'.", ephemeral=True
            )
            return False

        user = interaction.user
        for role in user.roles:
            if role.permissions.administrator or callback_check(user, object, permission):
                return True

        await interaction.response.send_message(
            f"Vous n'avez pas la permission '{permission}' pour l'objet '{any_variable}'.",
            ephemeral=True,
        )
        return False

    return discord.app_commands.check(predicate)


def check_permission_restaurant(param: str, permission: str) -> bool:
    return check_permission(
        param,
        get_restaurant_object,
        has_restaurant_permission,
        permission,
    )
