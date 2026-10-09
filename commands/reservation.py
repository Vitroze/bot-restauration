from datetime import datetime, time
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands
from models.reservations import ReservationModal
from utils.manage_reservations import get_reservations_by_user

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
async def setup(bot):
    await bot.add_cog(Reservations(bot))