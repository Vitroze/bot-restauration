import discord
from datetime import timedelta, datetime, time
from zoneinfo import ZoneInfo
from utils.logger import printError
from utils.manage_restaurant import get_all_restaurants
from utils.manage_reservations import add_reservation

TZ = ZoneInfo("Europe/Paris")

class ReservationModal(discord.ui.Modal, title="Réservation"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    name_restaurant_label = discord.ui.Label(
        text="Nom du restaurant",
        component=discord.ui.Select(
            required=True,
            placeholder="Sélectionnez un restaurant",
            options=[
                discord.SelectOption(label=name, value=name) for name in get_all_restaurants().keys()
            ],
        ),
    )

    date_reservation = discord.ui.TextInput(
        label="Date de réservation (DD/MM/YYYY)",
        placeholder=f"Entrez la date de réservation (ex: {(datetime.now(TZ) + timedelta(days=1)).strftime('%d/%m/%Y')})",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        restaurant_name = self.name_restaurant_label.component.values[0]
        if restaurant_name not in get_all_restaurants():
            await interaction.response.send_message(f"Le restaurant '{restaurant_name}' n'existe pas.", ephemeral=True)
            return

        date = self.date_reservation.value

        try:
            date_obj = datetime.strptime(date, "%d/%m/%Y").date()
        except ValueError:
            await interaction.response.send_message("Format de date invalide. Veuillez utiliser le format DD/MM/YYYY.", ephemeral=True)
            return

        today = datetime.now(TZ).date()
        if date_obj <= today:
            await interaction.response.send_message("La date de réservation ne peut pas être dans le passé ou d'aujourd'hui.", ephemeral=True)
            return

        if date_obj > today + timedelta(days=30):
            await interaction.response.send_message("La date de réservation ne peut pas être à plus de 30 jours dans le futur.", ephemeral=True)
            return

        passed, message = await add_reservation(restaurant_name, date, interaction.user.id)
        if passed:
            dt = datetime.combine(date_obj, time.min, tzinfo=TZ)
            embed = discord.Embed(title="Réservation réussie", color=discord.Color.green())
            embed.add_field(name="Restaurant", value=restaurant_name, inline=False)
            embed.add_field(name="Date de réservation", value=discord.utils.format_dt(dt, style="D"), inline=False)
            embed.add_field(name="Dans combien de temps", value=discord.utils.format_dt(dt, style="R"), inline=False)
            embed.add_field(name="Location", value=f"[Voir sur Google Maps](https://www.google.com/maps/search/?api=1&query={restaurant_name.replace(' ', '+')})", inline=False)
            embed.set_footer(text="Merci d'avoir utilisé notre service de réservation !")
            try:
                await interaction.user.send(embed=embed)
                await interaction.response.send_message("Réservation réussie ! Un message privé vous a été envoyé avec les détails.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Réservation réussie, mais je n'ai pas pu vous envoyer un message privé. Veuillez vérifier vos paramètres de confidentialité. Détails de l'erreur: {e}", ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message("Une erreur est survenue lors de la soumission du formulaire.", ephemeral=True)
        printError("Reservations", f"Erreur lors de la soumission du formulaire: {error}")
