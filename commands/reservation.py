from datetime import datetime, time
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands
from ui import reservations
from ui.reservations import ReservationModal
from utils.manage_reservations import get_reservations_by_user, remove_reservation, get_all_reservations_by_restaurant
from utils.manage_restaurant import RestaurantTransformer
from models.restaurant import Restaurant
from utils.manage_permission import check_permission_restaurant

TZ = ZoneInfo("Europe/Paris")

class Reservations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reserver", description="Réserver une table dans un restaurant.")
    async def reserver(self, interaction: discord.Interaction):
        modal = ReservationModal(self.bot)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="mes_reservations", description="Voir vos réservations.")
    async def mes_reservations(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        reservations = await get_reservations_by_user(user_id)

        if not reservations:
            await interaction.response.send_message("Vous n'avez aucune réservation.", ephemeral=True)
            return

        embed = discord.Embed(title="Vos réservations", color=discord.Color.blue())
        embed.add_field(name="Nombre de réservations", value=str(len(reservations)), inline=False)
        embed.add_field(name="Détails des réservations", value="\u200b", inline=False)

        reservations = sorted(reservations, key=lambda r: r["date_reservation"])

        restaurants_col = []
        dates_col = []
        relative_col = []

        for res in reservations:
            try:
                date_obj = datetime.strptime(res["date_reservation"], "%d/%m/%Y").date()
            except ValueError:
                continue

            dt = datetime.combine(date_obj, time.min, tzinfo=TZ)

            restaurants_col.append(res["name_restaurant"])
            dates_col.append(discord.utils.format_dt(dt, style="D"))
            relative_col.append(discord.utils.format_dt(dt, style="R"))

        embed = discord.Embed(title="Vos réservations", color=discord.Color.blue())
        embed.add_field(name="Nombre de réservations", value=str(len(reservations)), inline=False)
        embed.add_field(name="Restaurant", value="\n".join(restaurants_col), inline=True)
        embed.add_field(name="Date", value="\n".join(dates_col), inline=True)
        embed.add_field(name="Combien temps", value="\n".join(relative_col), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="annuler_reservation", description="Annuler une réservation.")
    @app_commands.describe(restaurant="Nom du restaurant", date="Date de réservation (DD/MM/YYYY)")
    async def annuler_reservation(self, interaction: discord.Interaction, restaurant: str, date: str):
        user_id = interaction.user.id
        _, message = await remove_reservation(restaurant, date, user_id)
        await interaction.response.send_message(message, ephemeral=True)

    RestaurantNameTransformer = app_commands.Transform[Restaurant, RestaurantTransformer]

    @app_commands.command(name="restaurant_voir_reservations", description="Voir les réservations d'un restaurant.")
    @app_commands.describe(restaurant="Nom du restaurant")
    @check_permission_restaurant(param="restaurant", permission="see_reservations")
    async def restaurant_voir_reservations(self, interaction: discord.Interaction, restaurant: RestaurantNameTransformer, user: discord.User = None, hidden:bool = True):
        restaurant = restaurant.name if restaurant else None
        if not restaurant:
            await interaction.response.send_message("Le restaurant spécifié n'existe pas.", ephemeral=True)
            return

        restaurant_reservations = await get_reservations_by_user(user.id, restaurant) if user else await get_all_reservations_by_restaurant(restaurant)

        if not restaurant_reservations:
            await interaction.response.send_message(f"Aucune réservation trouvée pour le restaurant ``{restaurant}``.", ephemeral=True)
            return

        sExtendedTitle = user and f" - {user.display_name}" or ""

        embed = discord.Embed(title=f"Réservations pour {restaurant} {sExtendedTitle}", color=discord.Color.blue())
        embed.add_field(name="Nombre de réservations", value=str(len(restaurant_reservations)), inline=False)

        dates_col = []
        relative_col = []
        user_col = []

        for res in restaurant_reservations:
            try:
                date_obj = datetime.strptime(res["date_reservation"], "%d/%m/%Y").date()
            except ValueError:
                continue

            dt = datetime.combine(date_obj, time.min, tzinfo=TZ)

            if not user:
                user_get = self.bot.get_user(res["user_id"]) or await self.bot.fetch_user(res["user_id"])
                user_col.append(user_get.mention if user_get else f"Utilisateur ID: {res['user_id']}")

            dates_col.append(discord.utils.format_dt(dt, style="D"))
            relative_col.append(discord.utils.format_dt(dt, style="R"))

        embed.add_field(name="Date", value="\n".join(dates_col), inline=True)
        if not user:
            embed.add_field(name="Utilisateur", value="\n".join(user_col), inline=True)
        embed.add_field(name="Combien temps", value="\n".join(relative_col), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=hidden)

async def setup(bot):
    await bot.add_cog(Reservations(bot))