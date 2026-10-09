import discord
from discord import app_commands
from discord.ext import commands
from ui.config_restaurant import ConfigRestaurantView
from utils.logger import printMessage, printError, printLog
from utils.manage_restaurant import *
from models.restaurant import Restaurant, RestaurantType
from utils.manage_permission import check_permission_restaurant
from utils.manage_ticket import TYPE_TICKET
from utils.function_utils import is_valid_emoji

printMessage("Config", "Chargement de l'extension : config")

PREFIX = "cfg_"
ALL_TYPES_PERMISSIONS_RESTAURANT = {
    "edit_restaurant": "Modifier les informations du restaurant",
    "view_config": "Voir la configuration du restaurant",
    "manage_reservations": "Gérer les réservations du restaurant",
    "see_reservations": "Voir les réservations du restaurant",
    "manage_tickets": "Gérer les tickets du restaurant",
    "add_item_menu": "Ajouter un item au menu d'un restaurant",
    "edit_item_menu": "Modifier un item du menu d'un restaurant",
    "remove_item_menu": "Supprimer un item du menu d'un restaurant",
    "take_command": "Prendre une commande dans le restaurant",
}

@app_commands.guild_only()
class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    RestaurantNameTransformer = app_commands.Transform[Restaurant, RestaurantTransformer]
    RestaurantTypeTransformer = app_commands.Transform[RestaurantType, RestaurantTypeTransformer]

    @app_commands.command(name=f"{PREFIX}restaurant", description="Gère les restaurants.")
    @app_commands.checks.has_permissions(administrator=True)
    async def manage_restaurant(self, interaction: discord.Interaction):
        view = ConfigRestaurantView(interaction.user.id)
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)
        view.origin = interaction
        view.message = await interaction.original_response()

    @app_commands.command(name=f"{PREFIX}vresto_create", description="Crée un restaurant.")
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

    ## ==================
    ## TYPE
    ## ==================
    @app_commands.command(name=f"{PREFIX}vresto_create_type", description="Crée un type de restaurant.")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_restaurant_type(self, interaction: discord.Interaction, name: str):
        if is_existing_restaurant_type(name):
            await interaction.response.send_message(f"Le type de restaurant `{name}` existe déjà.", ephemeral=True)
            return

        new_restaurant_type = RestaurantType(name)
        save_restaurant_type(new_restaurant_type)

        await interaction.response.send_message(f"Le type de restaurant `{name}` a été créé avec succès.")

    @app_commands.command(name=f"{PREFIX}vresto_delete_type", description="Supprime un type de restaurant existant.")
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
    @app_commands.command(name=f"{PREFIX}vresto_channel_ticket", description="Configurer le salon de ticket pour un restaurant.")
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

    @app_commands.command(name=f"{PREFIX}vresto_emoji_ticket", description="Configurer l'emoji de ticket pour un restaurant.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(emoji="L'emoji à configurer pour les tickets")
    async def setup_ticket_emoji(self, interaction: discord.Interaction, emoji: str):
        if self.bot is None:
            await interaction.response.send_message("Le bot n'est pas initialisé correctement.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Vérifier si c'est un emoji valide (unicode ou custom)
        is_emoji_valid = await is_valid_emoji(self, emoji)
        if not is_emoji_valid:
            await interaction.response.send_message("L'emoji spécifié n'est pas valide. Veuillez fournir un emoji unicode ou un emoji personnalisé du serveur.", ephemeral=True)
            return

        if self.bot.get_cog("TicketManager") is None:
            await interaction.response.send_message("Le système de ticket n'est pas initialisé correctement.", ephemeral=True)
            return

        self.bot.get_cog("TicketManager").config_ticket_emoji = emoji
        await self.bot.get_cog("TicketManager").setup_config_channel(self.bot.get_cog("TicketManager").config_channel)
        await interaction.followup.send(f"L'emoji de ticket a été configuré avec succès : {emoji}", ephemeral=True)

    @app_commands.command(name=f"{PREFIX}vresto_category_ticket", description="Configurer la catégorie de ticket pour un type de ticket.")
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

    ## =================
    ## Menu
    ## =================

    @app_commands.command(name=f"{PREFIX}vresto_add_menu_item", description="Ajouter un item au menu d'un restaurant.")
    @check_permission_restaurant(param="restaurant_name", permission="add_item_menu")
    @app_commands.describe(restaurant_name="Le nom du restaurant")
    @app_commands.describe(item_name="Le nom de l'item à ajouter")
    @app_commands.describe(item_description="La description de l'item à ajouter")
    @app_commands.describe(item_price="Le prix de l'item à ajouter")
    @app_commands.describe(item_picture_url="L'URL de l'image de l'item à ajouter (optionnel)")
    async def add_menu_item(self, interaction: discord.Interaction, restaurant_name: RestaurantNameTransformer, item_name: str, item_description: str, item_price: float, item_picture_url: str = None):
        restaurant_name = restaurant_name.name if restaurant_name else None
        if not restaurant_name:
            await interaction.response.send_message("Le restaurant spécifié n'existe pas.", ephemeral=True)
            return

        restaurant = get_all_restaurants().get(restaurant_name)
        if not restaurant:
            await interaction.response.send_message(f"Le restaurant `{restaurant_name}` n'existe pas.", ephemeral=True)
            return

        if getattr(restaurant, 'menu', None):
            restaurant['menu'] = []

        if any(item['name'].lower() == item_name.lower() for item in restaurant['menu']):
            await interaction.response.send_message(f"L'item `{item_name}` existe déjà dans le menu du restaurant `{restaurant_name}`.", ephemeral=True)
            return

        new_item = {
            "name": item_name,
            "description": item_description,
            "price": item_price,
            "picture_url": item_picture_url
        }

        restaurant['menu'].append(new_item)
        await save_restaurant(Restaurant(**restaurant))

        await interaction.response.send_message(f"L'item `{item_name}` a été ajouté au menu du restaurant `{restaurant_name}` avec succès.")

    @app_commands.command(name=f"{PREFIX}vresto_remove_menu_item", description="Supprimer un item du menu d'un restaurant.")
    @check_permission_restaurant(param="restaurant_name", permission="remove_item_menu")
    @app_commands.describe(restaurant_name="Le nom du restaurant")
    @app_commands.describe(item_name="Le nom de l'item à supprimer")
    async def remove_menu_item(self, interaction: discord.Interaction, restaurant_name: RestaurantNameTransformer, item_name: str):
        restaurant_name = restaurant_name.name if restaurant_name else None
        if not restaurant_name:
            await interaction.response.send_message("Le restaurant spécifié n'existe pas.", ephemeral=True)
            return

        restaurant = get_all_restaurants().get(restaurant_name)
        if not restaurant:
            await interaction.response.send_message(f"Le restaurant `{restaurant_name}` n'existe pas.", ephemeral=True)
            return

        item_to_remove = next((item for item in restaurant['menu'] if item['name'].lower() == item_name.lower()), None)
        if not item_to_remove:
            await interaction.response.send_message(f"L'item `{item_name}` n'existe pas dans le menu du restaurant `{restaurant_name}`.", ephemeral=True)
            return

        restaurant['menu'].remove(item_to_remove)
        await save_restaurant(Restaurant(**restaurant))

        await interaction.response.send_message(f"L'item `{item_name}` a été supprimé du menu du restaurant `{restaurant_name}` avec succès.")

    @app_commands.command(name=f"{PREFIX}vresto_edit_menu_item", description="Modifier un item du menu d'un restaurant.")
    @check_permission_restaurant(param="restaurant_name", permission="edit_item_menu")
    @app_commands.describe(restaurant_name="Le nom du restaurant")
    @app_commands.describe(item_name="Le nom de l'item à modifier")
    @app_commands.describe(new_item_name="Le nouveau nom de l'item (optionnel)")
    @app_commands.describe(new_item_description="La nouvelle description de l'item (optionnel)")
    @app_commands.describe(new_item_price="Le nouveau prix de l'item (optionnel)")
    @app_commands.describe(new_item_picture_url="La nouvelle URL de l'image de l'item (optionnel)")
    async def edit_menu_item(self, interaction: discord.Interaction, restaurant_name: RestaurantNameTransformer, item_name: str, new_item_name: str = None, new_item_description: str = None, new_item_price: float = None, new_item_picture_url: str = None):
        restaurant_name = restaurant_name.name if restaurant_name else None
        if not restaurant_name:
            await interaction.response.send_message("Le restaurant spécifié n'existe pas.", ephemeral=True)
            return

        restaurant = get_all_restaurants().get(restaurant_name)
        if not restaurant:
            await interaction.response.send_message(f"Le restaurant `{restaurant_name}` n'existe pas.", ephemeral=True)
            return

        item_to_edit = next((item for item in restaurant['menu'] if item['name'].lower() == item_name.lower()), None)
        if not item_to_edit:
            await interaction.response.send_message(f"L'item `{item_name}` n'existe pas dans le menu du restaurant `{restaurant_name}`.", ephemeral=True)
            return

        if new_item_name:
            item_to_edit['name'] = new_item_name
        if new_item_description:
            item_to_edit['description'] = new_item_description
        if new_item_price is not None:
            item_to_edit['price'] = new_item_price
        if new_item_picture_url:
            item_to_edit['picture_url'] = new_item_picture_url

        await save_restaurant(Restaurant(**restaurant))

        await interaction.response.send_message(f"L'item `{item_name}` a été modifié dans le menu du restaurant `{restaurant_name}` avec succès.")

async def setup(bot):
    await bot.add_cog(Config(bot))