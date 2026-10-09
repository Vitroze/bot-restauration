import discord
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from discord.ext import tasks, commands

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
                date_obj = datetime.strptime(res["date_reservation"], "%Y-%m-%d").date()
            except ValueError:
                continue

            dt = datetime.combine(date_obj, time.min, tzinfo=TZ)
            if now >= dt:
                continue

            deja_envoyes = res.setdefault("rappels_envoyes", [])
            dus = [
                label for label, delta in RAPPELS.items()
                if now >= dt - delta and label not in deja_envoyes
            ]
            if not dus:
                continue

            deja_envoyes.extend(dus)
            modifie = True
            await self.envoyer_rappel(res, dt)

        if modifie:
            await save_reservations_to_file(reservations)

    async def envoyer_rappel(self, res: dict, dt: datetime):
        try:
            user = self.bot.get_user(res["user_id"]) or await self.bot.fetch_user(res["user_id"])
            embed = discord.Embed(title="Rappel de réservation", color=discord.Color.orange())
            embed.add_field(name="Restaurant", value=res["name_restaurant"], inline=False)
            embed.add_field(name="Date de réservation", value=discord.utils.format_dt(dt, "D"), inline=False)
            embed.add_field(name="Dans combien de temps", value=discord.utils.format_dt(dt, "R"), inline=False)
            embed.set_footer(text="Ceci est un rappel pour votre réservation.")
            await user.send(embed=embed)
        except discord.NotFound:
            print(f"Utilisateur {res['user_id']} introuvable.")
        except discord.Forbidden:
            print(f"MP fermés pour l'utilisateur {res['user_id']}.")
        except discord.HTTPException as e:
            print(f"Erreur d'envoi du rappel : {e!r}")

    @check_reservations.before_loop
    async def before_check_reservations(self):
        await self.bot.wait_until_ready()

    @check_reservations.error
    async def check_reservations_error(self, error):
        print(f"La boucle de rappel a planté : {error!r}")
# Setup
async def setup(bot):
    await bot.add_cog(Rappel(bot))