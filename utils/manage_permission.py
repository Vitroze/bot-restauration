import discord
from .manage_restaurant import get_restaurant_object

def check_permission_restaurant(param:str, permission: str) -> bool:
    async def predicate(interaction: discord.Interaction) -> bool:
        restaurant = getattr(interaction.namespace, param, None)
        restaurant_object = get_restaurant_object(restaurant)
        if restaurant_object is None:
            await interaction.response.send_message(f"Le restaurant '{restaurant}' n'existe pas.", ephemeral=True)
            return False

        user = interaction.user
        has_permission = False  # Replace with actual permission checking logic
        for role in user.roles:
            if role.permissions.administrator or restaurant_object.has_permission(role.id, permission):
                has_permission = True
                break

        if not has_permission:
            await interaction.response.send_message(f"Vous n'avez pas la permission '{permission}' pour le restaurant '{restaurant}'.", ephemeral=True)
            return False

        return True


    return discord.app_commands.check(predicate)