import os
import asyncio
import discord
import traceback
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from utils.manage_restaurant import load_all_restaurants
from utils.manage_ticket import TicketManager
from ui.order_ticket import TakeOrderButton, CloseOrderButton
from models.rappels import Rappel
from utils.logger import printMessage, printError, printLog

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

class RegisterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.synced = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self.synced:
            return

        try:
            guild = discord.Object(id=858647206394200064)
            printMessage("Main", f"Connecté en tant que {self.bot.user}")
            self.bot.tree.copy_global_to(guild=guild)
            self.bot.tree.on_error = self.on_log_error
            await load_all_restaurants()

            self.ticket_cog = TicketManager(self.bot)
            await self.bot.add_cog(self.ticket_cog)

            self.rappel_cog = Rappel(self.bot)
            await self.bot.add_cog(self.rappel_cog)

            synced = await self.bot.tree.sync(guild=guild)
            printMessage("RegisterCommands", f"Commandes slash synchronisées : {len(synced)}")
            self.synced = True

        except Exception as e:
            printError("RegisterCommands", f"Erreur ({type(e).__name__}) lors de la synchronisation des commandes : {e}")

    @commands.Cog.listener()
    async def on_log_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
            return

        printError("RegisterCommands", f"Erreur ({type(error).__name__}) lors de l'exécution de la commande '{interaction.command.name}' : {error}")
        printError("RegisterCommands", f"Traceback : {traceback.format_exc()}")

        if interaction.response.is_done():
            await interaction.followup.send(f"Une erreur est survenue lors de l'exécution de la commande. Si vous êtes un administrateur, veuillez vérifier les logs pour plus d'informations.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Une erreur est survenue lors de l'exécution de la commande. Si vous êtes un administrateur, veuillez vérifier les logs pour plus d'informations.", ephemeral=True)

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        printError("Main", f"Erreur ({type(event_method).__name__}) dans l'événement {event_method.__name__} : {args}, {kwargs}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        printLog("Main", f"Nouvel utilisateur : {member.name}#{member.discriminator} ({member.id})")
        try:
            await member.send(f"Bienvenue à toi sur le serveur {member.guild.name} !")
        except discord.Forbidden:
            printError("Main", f"Impossible d'envoyer un message privé à {member.name}#{member.discriminator}.")

async def main():
    os.system("cls" if os.name == "nt" else "clear")  # Clear the console for better readability
    discord.utils.setup_logging()

    async with bot:
        for filename in os.listdir("./commands"):
            if filename.endswith(".py"):
                printMessage("RegisterCommands", f"Chargement de l'extension : {filename[:-3]}")
                await bot.load_extension(f"commands.{filename[:-3]}")

        printMessage("Main", "Enregistrement des boutons dynamiques...")
        bot.add_dynamic_items(TakeOrderButton, CloseOrderButton)
        printMessage("Main", "Démarrage du bot...")
        await bot.add_cog(RegisterCommands(bot))
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())