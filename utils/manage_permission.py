import inspect
from typing import Callable

import discord

from .manage_restaurant import get_restaurant_object


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
        lambda user, restaurant, permission: restaurant.has_permission(user.id, permission),
        permission,
    )
