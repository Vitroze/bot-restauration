from functools import partial
from pyexpat.errors import messages

import discord
from discord import app_commands
from discord.ext import commands
from main import printMessage
from utils.manage_restaurant import *
from models.restaurant import Restaurant, RestaurantType
from utils.manage_permission import check_permission_restaurant
from utils.manage_ticket import TYPE_TICKET

printMessage("Config", "Chargement de l'extension : config")

PREFIX = "cfg_"
ALL_TYPES_PERMISSIONS_RESTAURANT = [
    "edit_restaurant",
    "view_config",
]

@app_commands.guild_only()
class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    RestaurantNameTransformer = app_commands.Transform[Restaurant, RestaurantTransformer]
    RestaurantTypeTransformer = app_commands.Transform[RestaurantType, RestaurantTypeTransformer]

    @app_commands.command(name=f"{PREFIX}create_restaurant", description="Crée un restaurant.")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_restaurant(self, interaction: discord.Interaction, name: str, description: str, type_restaurant: RestaurantTypeTransformer, location: str):
        if is_existing_restaurant(name):
            await interaction.response.send_message(f"Le restaurant `{name}` existe déjà.", ephemeral=True)
            return

        if not is_existing_restaurant_type(type_restaurant.to_name()):
            await interaction.response.send_message(f"Le type_restaurant de restaurant `{type_restaurant}` n'existe pas. Veuillez créer le type_restaurant de restaurant avant de créer le restaurant.", ephemeral=True)
            return

        new_restaurant = Restaurant(name=name, description=description, type=type_restaurant.to_name(), location=location)
        saved = await save_restaurant(new_restaurant)

        if not saved:
            await interaction.response.send_message(f"Une erreur est survenue lors de la création du restaurant `{name}`.", ephemeral=True)
            return

        await interaction.response.send_message(f"Le restaurant `{name}` a été créé avec succès.")

    @app_commands.command(name=f"{PREFIX}edit_restaurant", description="Modifie un restaurant existant.")
    #@app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(restaurant_name="Le nom du restaurant à modifier")
    @app_commands.describe(new_description="La nouvelle description du restaurant")
    @app_commands.describe(new_type="Le nouveau type du restaurant")
    @app_commands.describe(new_location="La nouvelle localisation du restaurant")
    @check_permission_restaurant(param="restaurant_name", permission="edit_restaurant")
    async def edit_restaurant(self, interaction: discord.Interaction, restaurant_name: RestaurantNameTransformer, new_description: str = None, new_type: RestaurantTypeTransformer = None, new_location: str = None):
        restaurant = get_all_restaurants().get(restaurant_name)

        if not restaurant:
            await interaction.response.send_message(f"Le restaurant `{restaurant_name}` n'existe pas.", ephemeral=True)
            return

        if new_description is None and new_type is None and new_location is None:
            await interaction.response.send_message(f"Aucune modification n'a été spécifiée pour le restaurant `{restaurant_name}`.", ephemeral=True)
            return

        if new_description:
            restaurant["description"] = new_description
        if new_type and is_existing_restaurant_type(new_type.name):
            restaurant["type"] = new_type.name
        if new_location:
            restaurant["location"] = new_location

        await save_restaurant(Restaurant(**restaurant))
        await interaction.response.send_message(f"Le restaurant `{restaurant_name}` a été modifié avec succès.")

    @app_commands.command(name=f"{PREFIX}delete_restaurant", description="Supprime un restaurant existant.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(restaurant_name="Le nom du restaurant à supprimer")
    async def delete_restaurant(self, interaction: discord.Interaction, restaurant_name: RestaurantNameTransformer):
        if not is_existing_restaurant(restaurant_name):
            await interaction.response.send_message(f"Le restaurant `{restaurant_name}` n'existe pas.", ephemeral=True)
            return

        delete_restaurant(restaurant_name)

        await interaction.response.send_message(f"Le restaurant `{restaurant_name}` a été supprimé avec succès.")

    @app_commands.command(name=f"{PREFIX}add_perm_restaurant", description="Ajoute une permission à un rôle pour un restaurant spécifique.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(restaurant_name="Le nom du restaurant")
    @app_commands.describe(role="Le rôle auquel ajouter la permission")
    @app_commands.describe(permission="La permission à ajouter")
    # @app_commands.choices(permission=[app_commands.Choice(name=perm, value=perm) for perm in ALL_TYPES_PERMISSIONS_RESTAURANT])
    async def add_perm_restaurant(self, interaction: discord.Interaction, restaurant_name: RestaurantNameTransformer, role: discord.Role, permission: str):
        restaurant = get_all_restaurants().get(restaurant_name)
        if not restaurant:
            await interaction.response.send_message(f"Le restaurant `{restaurant_name}` n'existe pas.", ephemeral=True)
            return

        if role is None:
            await interaction.response.send_message(f"Le rôle spécifié n'existe pas.", ephemeral=True)
            return

        if role.permissions.administrator:
            await interaction.response.send_message(f"Le rôle `{role.name}` est un rôle administrateur et a déjà toutes les permissions.", ephemeral=True)
            return

        if role.is_default():
            await interaction.response.send_message(f"Le rôle `{role.name}` est un rôle spécial et ne peut pas avoir de permissions spécifiques.", ephemeral=True)
            return

        if permission not in ALL_TYPES_PERMISSIONS_RESTAURANT:
            sJoin = ">,\n".join(ALL_TYPES_PERMISSIONS_RESTAURANT)
            await interaction.response.send_message(f"La permission `{permission}` n'est pas valide. Les permissions valides sont : {sJoin}.", ephemeral=True)
            return

        if role.id in restaurant["permissions"] and permission in restaurant["permissions"][role.id]:
            await interaction.response.send_message(f"Le rôle `{role.name}` a déjà la permission `{permission}` pour le restaurant `{restaurant_name}`.", ephemeral=True)
            return

        restaurant_object = Restaurant(**restaurant)
        restaurant_object.add_permission(role.id, permission)
        await save_restaurant(restaurant_object)

        await interaction.response.send_message(f"La permission `{permission}` a été ajoutée au rôle `{role.name}` pour le restaurant `{restaurant_name}`.")

    @add_perm_restaurant.autocomplete("permission")
    async def permission_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        name = interaction.namespace.restaurant_name
        if not name:
            return []
        restaurant = get_all_restaurants().get(name)
        if not restaurant:
            return []

        role = interaction.namespace.role
        if role is None or role.id in restaurant["permissions"]:
            return []

        return [
            app_commands.Choice(name=perm, value=perm) for perm in ALL_TYPES_PERMISSIONS_RESTAURANT if current.lower() in perm.lower()
        ][:25]

    @app_commands.command(name=f"{PREFIX}remove_perm_restaurant", description="Supprime une permission d'un rôle pour un restaurant spécifique.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(restaurant_name="Le nom du restaurant")
    @app_commands.describe(role="Le rôle auquel supprimer la permission")
    @app_commands.describe(permission="La permission à supprimer")
    #@app_commands.choices(permission=[app_commands.Choice(name="Toutes les permissions", value="*")] + [app_commands.Choice(name=perm, value=perm) for perm in ALL_TYPES_PERMISSIONS_RESTAURANT])

    async def remove_perm_restaurant(self, interaction: discord.Interaction, restaurant_name: RestaurantNameTransformer, role: discord.Role, permission: str):
        restaurant = get_all_restaurants().get(restaurant_name)
        if not restaurant:
            await interaction.response.send_message(f"Le restaurant `{restaurant_name}` n'existe pas.", ephemeral=True)
            return

        if role is None:
            await interaction.response.send_message(f"Le rôle spécifié n'existe pas.", ephemeral=True)
            return

        if role.permissions.administrator:
            await interaction.response.send_message(f"Le rôle `{role.name}` est un rôle administrateur et ne peut pas avoir de permissions spécifiques supprimées.", ephemeral=True)
            return

        if role.is_default():
            await interaction.response.send_message(f"Le rôle `{role.name}` est un rôle spécial et ne peut pas avoir de permissions spécifiques supprimées.", ephemeral=True)
            return

        if permission != "*" and permission not in ALL_TYPES_PERMISSIONS_RESTAURANT:
            sJoin = ">,\n".join(ALL_TYPES_PERMISSIONS_RESTAURANT)
            await interaction.response.send_message(f"La permission `{permission}` n'est pas valide. Les permissions valides sont : {sJoin}.", ephemeral=True)
            return

        if role.id not in restaurant["permissions"] or permission != "*" and permission not in restaurant["permissions"][role.id]:
            await interaction.response.send_message(f"Le rôle `{role.name}` n'a pas la permission `{permission}` pour le restaurant `{restaurant_name}`.", ephemeral=True)
            return

        restaurant_object = Restaurant(**restaurant)
        if permission == "*":
            del restaurant_object.permissions[role.id]
        else:
            restaurant_object.remove_permission(role.id, permission)
        await save_restaurant(restaurant_object)

        if permission == "*":
            await interaction.response.send_message(f"Toutes les permissions ont été supprimées du rôle `{role.name}` pour le restaurant `{restaurant_name}`.")
        else:
            await interaction.response.send_message(f"La permission `{permission}` a été supprimée du rôle `{role.name}` pour le restaurant `{restaurant_name}`.")

    # auto complete the role permission for a restaurant
    @remove_perm_restaurant.autocomplete("permission")
    async def permission_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        name = interaction.namespace.restaurant_name
        if not name:
            return []
        restaurant = get_all_restaurants().get(name)
        if not restaurant:
            return []

        role = interaction.namespace.role
        if role is None or role.id not in restaurant["permissions"]:
            return []

        return ([
            app_commands.Choice(name="Toutes les permissions", value="*")
        ] + [
            app_commands.Choice(name=perm, value=perm) for perm in restaurant["permissions"][role.id] if current.lower() in perm.lower()
        ])[:25]

    @app_commands.command(name=f"{PREFIX}see_restaurant", description="Affiche les permissions d'un restaurant.")
    @check_permission_restaurant(param="restaurant_name", permission="view_config")
    @app_commands.describe(restaurant_name="Le nom du restaurant à afficher")
    @app_commands.describe(hidden="Si le message doit être visible uniquement par vous (True) ou public (False)")
    async def see_restaurant(self, interaction: discord.Interaction, restaurant_name: RestaurantNameTransformer, hidden:bool=True):
        restaurant = get_all_restaurants().get(restaurant_name)
        if not restaurant:
            await interaction.response.send_message(f"Le restaurant `{restaurant_name}` n'existe pas.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Restaurant: {restaurant['name']}", description=restaurant['description'], color=discord.Color.blue())
        embed.add_field(name="Type", value=restaurant['type'], inline=False)
        embed.add_field(name="Location", value=restaurant['location'], inline=False)
        embed.add_field(name="Reservations", value=str(len(restaurant['reservations'])), inline=False)

        roles_col = []
        perms_col = []

        for role_id, perms in restaurant["permissions"].items():
            role = interaction.guild.get_role(int(role_id))
            roles_col.append(role.mention if role else f"`{role_id}`")
            perms_col.append(", ".join(f"`{p}`" for p in perms) or "Aucune")

        embed.add_field(name="Rôle", value="\n".join(roles_col) or "Aucun", inline=True)
        embed.add_field(name="Permissions", value="\n".join(perms_col) or "Aucune", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=hidden)

    ## ==================
    ## TYPE
    ## ==================

    @app_commands.command(name=f"{PREFIX}create_restaurant_type", description="Crée un type de restaurant.")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_restaurant_type(self, interaction: discord.Interaction, name: str):
        if is_existing_restaurant_type(name):
            await interaction.response.send_message(f"Le type de restaurant `{name}` existe déjà.", ephemeral=True)
            return

        new_restaurant_type = RestaurantType(name)
        save_restaurant_type(new_restaurant_type)

        await interaction.response.send_message(f"Le type de restaurant `{name}` a été créé avec succès.")

    @app_commands.command(name=f"{PREFIX}delete_restaurant_type", description="Supprime un type de restaurant existant.")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_restaurant_type(self, interaction: discord.Interaction, name: RestaurantTypeTransformer):
        if not is_existing_restaurant_type(name):
            await interaction.response.send_message(f"Le type de restaurant `{name}` n'existe pas.", ephemeral=True)
            return

        delete_restaurant_type(name)

        await interaction.response.send_message(f"Le type de restaurant `{name}` a été supprimé avec succès.")

    ## =================
    ## Ticket
    ## =================

    async def is_valid_emoji(self, emoji: str) -> bool:
        emoji = emoji.strip()

        if emoji.startswith("<") and emoji.endswith(">"):
            try:
                partial_emoji = discord.PartialEmoji.from_str(emoji)
            except Exception:
                return False
            return partial_emoji.id is not None and self.bot.get_emoji(partial_emoji.id) is not None

        if discord.utils.get(self.bot.emojis, name=emoji) is not None:
            return True

        if emoji.isdigit() and self.bot.get_emoji(int(emoji)) is not None:
            return True

        return bool(emoji) and not emoji.isascii()

    @app_commands.command(name=f"{PREFIX}channel_ticket", description="Configurer le salon de ticket pour un restaurant.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Le salon à configurer pour les tickets")
    async def setup_ticket_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if self.bot is None:
            await interaction.response.send_message("Le bot n'est pas initialisé correctement.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if self.bot.get_cog("TicketManager") is None:
            await interaction.response.send_message("Le système de ticket n'est pas initialisé correctement.", ephemeral=True)
            return

        await self.bot.get_cog("TicketManager").setup_config_channel(channel)
        await interaction.followup.send(f"Le salon de ticket a été configuré avec succès : {channel.mention}", ephemeral=True)

    @app_commands.command(name=f"{PREFIX}emoji_ticket", description="Configurer l'emoji de ticket pour un restaurant.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(emoji="L'emoji à configurer pour les tickets")
    async def setup_ticket_emoji(self, interaction: discord.Interaction, emoji: str):
        if self.bot is None:
            await interaction.response.send_message("Le bot n'est pas initialisé correctement.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Vérifier si c'est un emoji valide (unicode ou custom)
        is_emoji_valid = await self.is_valid_emoji(emoji)
        if not is_emoji_valid:
            await interaction.response.send_message("L'emoji spécifié n'est pas valide. Veuillez fournir un emoji unicode ou un emoji personnalisé du serveur.", ephemeral=True)
            return

        if self.bot.get_cog("TicketManager") is None:
            await interaction.response.send_message("Le système de ticket n'est pas initialisé correctement.", ephemeral=True)
            return

        self.bot.get_cog("TicketManager").config_ticket_emoji = emoji
        await self.bot.get_cog("TicketManager").setup_config_channel(self.bot.get_cog("TicketManager").config_channel)
        await interaction.followup.send(f"L'emoji de ticket a été configuré avec succès : {emoji}", ephemeral=True)

    @app_commands.command(name=f"{PREFIX}category_ticket", description="Configurer la catégorie de ticket pour un type de ticket.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(ticket_type="Le type de ticket à configurer")
    @app_commands.describe(category="La catégorie à configurer pour le type de ticket")
    @app_commands.choices(ticket_type=[app_commands.Choice(name=key, value=key) for key in TYPE_TICKET.keys()])
    async def setup_ticket_category(self, interaction: discord.Interaction, ticket_type: str, category: discord.CategoryChannel):
        if self.bot is None:
            await interaction.response.send_message("Le bot n'est pas initialisé correctement.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if self.bot.get_cog("TicketManager") is None:
            await interaction.response.send_message("Le système de ticket n'est pas initialisé correctement.", ephemeral=True)
            return

        TYPE_TICKET[ticket_type] = category.id
        await self.bot.get_cog("TicketManager").setup_config_channel(self.bot.get_cog("TicketManager").config_channel)
        await interaction.followup.send(f"La catégorie pour le type de ticket `{ticket_type}` a été configurée avec succès : {category.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Config(bot))