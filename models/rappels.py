import discord
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from discord.ext import tasks, commands
from utils.logger import printMessage, printError, printLog
import traceback

from utils.manage_reservations import get_all_reservations, save_reservations_to_file

TZ = ZoneInfo("Europe/Paris")

RAPPELS = {
    "30_minutes": timedelta(minutes=30),
    "1_hour": timedelta(hours=1),
    "2_hours": timedelta(hours=2),
    "6_hours": timedelta(hours=6),
    "12_hours": timedelta(hours=12),
    "1_day": timedelta(days=1),
    "2_days": timedelta(days=2),
}


class Rappel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.check_reservations.start()

    async def cog_unload(self):
        self.check_reservations.cancel()

    @tasks.loop(minutes=1)
    async def check_reservations(self):
        now = datetime.now(TZ)
        reservations = await get_all_reservations()
        modifie = False

        for res in reservations:
            try:
                date_obj = datetime.strptime(res["date_reservation"], "%d/%m/%Y").date()
            except ValueError:
                reservations.remove(res)
                modifie = True
                continue

            dt = datetime.combine(date_obj, time.min, tzinfo=TZ)
            if now >= dt:
                continue

            already_send = res.setdefault("already_sent", [])
            dus = [
                label for label, delta in RAPPELS.items()
                if now >= dt - delta and label not in already_send
            ]

            if not dus:
                continue

            already_send.extend(dus)
            modifie = True

            await self.send_rappel(res, dt, min(dus, key=lambda label: RAPPELS[label]))

        if modifie:
            await save_reservations_to_file(reservations)

    async def format_date(self, date_str: str) -> datetime:
        """
        30_minutes -> 30 minutes
        2_hours -> 2 heures
        2_days -> 2 jours
        """

        if date_str.endswith("_minutes"):
            return f"{date_str.split('_')[0]} minutes"
        elif date_str.endswith("_hours"):
            return f"{date_str.split('_')[0]} heures"
        elif date_str.endswith("_days"):
            return f"{date_str.split('_')[0]} jours"
        else:
            return date_str

    async def send_rappel(self, res: dict, dt: datetime, rappel: str):
        try:
            user = self.bot.get_user(res["user_id"]) or await self.bot.fetch_user(res["user_id"])
            embed = discord.Embed(title=f"Rappel de réservation ({await self.format_date(rappel)})", color=discord.Color.orange())
            embed.add_field(name="Restaurant", value=res["name_restaurant"], inline=False)
            embed.add_field(name="Date de réservation", value=discord.utils.format_dt(dt, "D"), inline=False)
            embed.add_field(name="Dans combien de temps", value=discord.utils.format_dt(dt, "R"), inline=False)
            embed.set_footer(text="Ceci est un rappel pour votre réservation.")
            await user.send(embed=embed)
        except discord.NotFound:
            printError("Rappel", f"Utilisateur {res['user_id']} introuvable.")
        except discord.Forbidden:
            printError("Rappel", f"MP fermés pour l'utilisateur {res['user_id']}.")
        except discord.HTTPException as e:
            printError("Rappel", f"Erreur d'envoi du rappel : {e!r}")

    @check_reservations.before_loop
    async def before_check_reservations(self):
        await self.bot.wait_until_ready()

    @check_reservations.error
    async def check_reservations_error(self, error):
        printError("Rappel", f"La boucle de rappel a planté : {error!r}")
        printError("Rappel", f"Traceback : {traceback.format_exc()}")
# Setup
async def setup(bot):
    await bot.add_cog(Rappel(bot))