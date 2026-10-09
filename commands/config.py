import discord
from discord import app_commands
from discord.ext import commands

from models.restaurant import Restaurant, RestaurantType
from ui.config_restaurant import ConfigRestaurantView
from utils.function_utils import is_valid_emoji
from utils.logger import print_message
from utils.manage_restaurant import (
    RestaurantTransformer,
    RestaurantTypeTransformer,
    delete_restaurant_type,
    is_existing_restaurant,
    is_existing_restaurant_type,
    save_restaurant,
    save_restaurant_type,
)
from utils.manage_ticket import TYPE_TICKET

print_message("Config", "Chargement de l'extension : config")

PREFIX = "cfg_"


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

    @app_commands.command(name=f"{PREFIX}create_restaurant", description="Crée un restaurant.")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_restaurant(
        self,
        interaction: discord.Interaction,
        name: str,
        description: str,
        type_restaurant: RestaurantTypeTransformer,
        location: str,
    ):
        if is_existing_restaurant(name):
            await interaction.response.send_message(
                f"Le restaurant `{name}` existe déjà.", ephemeral=True
            )
            return

        if not is_existing_restaurant_type(type_restaurant.to_name()):
            await interaction.response.send_message(
                f"Le type_restaurant de restaurant `{type_restaurant}` n'existe pas. "
                f"Veuillez créer le type_restaurant de restaurant avant de créer le restaurant.",
                ephemeral=True,
            )
            return

        new_restaurant = Restaurant(
            name=name, description=description, type=type_restaurant.to_name(), location=location
        )
        saved = await save_restaurant(new_restaurant)

        if not saved:
            await interaction.response.send_message(
                f"Une erreur est survenue lors de la création du restaurant `{name}`.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(f"Le restaurant `{name}` a été créé avec succès.")

    # ==================
    # TYPE
    # ==================
    @app_commands.command(name=f"{PREFIX}create_type", description="Crée un type de restaurant.")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_restaurant_type(self, interaction: discord.Interaction, name: str):
        if is_existing_restaurant_type(name):
            await interaction.response.send_message(
                f"Le type de restaurant `{name}` existe déjà.", ephemeral=True
            )
            return

        new_restaurant_type = RestaurantType(name)
        save_restaurant_type(new_restaurant_type)

        await interaction.response.send_message(
            f"Le type de restaurant `{name}` a été créé avec succès."
        )

    @app_commands.command(
        name=f"{PREFIX}delete_type", description="Supprime un type de restaurant existant."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_restaurant_type(
        self, interaction: discord.Interaction, name: RestaurantTypeTransformer
    ):
        if not is_existing_restaurant_type(name):
            await interaction.response.send_message(
                f"Le type de restaurant `{name}` n'existe pas.", ephemeral=True
            )
            return

        delete_restaurant_type(name)

        await interaction.response.send_message(
            f"Le type de restaurant `{name}` a été supprimé avec succès."
        )

    # ==================
    # Ticket
    # ==================
    @app_commands.command(
        name=f"{PREFIX}channel_ticket",
        description="Configurer le salon de ticket pour un restaurant.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Le salon à configurer pour les tickets")
    async def setup_ticket_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        if self.bot is None:
            await interaction.response.send_message(
                "Le bot n'est pas initialisé correctement.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        if self.bot.get_cog("TicketManager") is None:
            await interaction.response.send_message(
                "Le système de ticket n'est pas initialisé correctement.", ephemeral=True
            )
            return

        await self.bot.get_cog("TicketManager").setup_config_channel(channel)
        await interaction.followup.send(
            f"Le salon de ticket a été configuré avec succès : {channel.mention}", ephemeral=True
        )

    @app_commands.command(
        name=f"{PREFIX}category_ticket",
        description="Configurer la catégorie de ticket pour un type de ticket.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(ticket_type="Le type de ticket à configurer")
    @app_commands.describe(category="La catégorie à configurer pour le type de ticket")
    @app_commands.choices(
        ticket_type=[app_commands.Choice(name=key, value=key) for key in TYPE_TICKET.keys()]
    )
    async def setup_ticket_category(
        self, interaction: discord.Interaction, ticket_type: str, category: discord.CategoryChannel
    ):
        if self.bot is None:
            await interaction.response.send_message(
                "Le bot n'est pas initialisé correctement.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        if self.bot.get_cog("TicketManager") is None:
            await interaction.response.send_message(
                "Le système de ticket n'est pas initialisé correctement.", ephemeral=True
            )
            return

        TYPE_TICKET[ticket_type] = category.id
        await self.bot.get_cog("TicketManager").setup_config_channel(
            self.bot.get_cog("TicketManager").config_channel
        )
        await interaction.followup.send(
            f"La catégorie pour le type de ticket `{ticket_type}` a été configurée "
            f"avec succès : {category.mention}",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Config(bot))
