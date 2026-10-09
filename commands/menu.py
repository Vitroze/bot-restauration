import discord
from discord import app_commands
from discord.ext import commands

from models.restaurant import Restaurant
from ui.menu import MenuUI
from utils.manage_restaurant import RestaurantTransformer


class Menu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    RestaurantNameTransformer = app_commands.Transform[Restaurant, RestaurantTransformer]

    @app_commands.command(name="menu", description="Affiche le menu d'un restaurant.")
    @app_commands.describe(restaurant="Le nom du restaurant dont vous voulez voir le menu.")
    async def menu(self, interaction: discord.Interaction, restaurant: RestaurantNameTransformer):
        if not restaurant:
            await interaction.response.send_message(
                "Le restaurant spécifié n'existe pas.", ephemeral=True
            )
            return

        if not restaurant.menu:
            await interaction.response.send_message(
                f"Le restaurant {restaurant.name} n'a pas de menu disponible.", ephemeral=True
            )
            return

        view = MenuUI(restaurant, restaurant.menu, interaction.user.id)
        await interaction.response.send_message(embed=view.build_embed(), view=view)
        view.message = await interaction.original_response()

    @app_commands.command(name="profile", description="Affiche le profil d'un restaurant.")
    @app_commands.describe(restaurant="Le nom du restaurant dont vous voulez voir le profil.")
    async def profile(
        self, interaction: discord.Interaction, restaurant: RestaurantNameTransformer
    ):
        if not restaurant:
            await interaction.response.send_message(
                "Le restaurant spécifié n'existe pas.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=restaurant.name,
            description=restaurant.description or "Aucune description disponible.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Type", value=restaurant.type or "Non spécifié", inline=True)
        embed.add_field(
            name="Localisation", value=restaurant.location or "Non spécifiée", inline=True
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Menu(bot))
