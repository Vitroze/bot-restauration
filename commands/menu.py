import asyncio
import math
import discord
from discord import app_commands
from discord.ext import commands
from models.restaurant import Restaurant
from utils.manage_restaurant import RestaurantTransformer

from ui.menu import MenuUI
from utils.function_utils import to_float, format_price

class Menu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    RestaurantNameTransformer = app_commands.Transform[Restaurant, RestaurantTransformer]

    @app_commands.command(name="menu", description="Affiche le menu d'un restaurant.")
    @app_commands.describe(restaurant="Le nom du restaurant dont vous voulez voir le menu.")
    async def menu(self, interaction: discord.Interaction, restaurant: RestaurantNameTransformer):
        if not restaurant:
            await interaction.response.send_message("Le restaurant spécifié n'existe pas.", ephemeral=True)
            return

        if not restaurant.menu:
            await interaction.response.send_message(
                f"Le restaurant {restaurant.name} n'a pas de menu disponible.", ephemeral=True
            )
            return

        view = MenuUI(restaurant, restaurant.menu, interaction.user.id)
        await interaction.response.send_message(embed=view.build_embed(), view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Menu(bot))