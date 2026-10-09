import os
import asyncio
import discord
import traceback
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from utils.manage_restaurant import load_all_restaurants
from utils.manage_ticket import TicketManager
from models.rappels import Rappel

load_dotenv()

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def printMessage(MODULE, message):
    print(f"{bcolors.OKGREEN}[VitrozeRestauration - {MODULE}] {message}{bcolors.ENDC}")

def printError(MODULE, message):
    print(f"{bcolors.FAIL}[VitrozeRestauration - {MODULE}] [ERREUR] : {message}{bcolors.ENDC}")

def printLog(MODULE, message):
    print(f"{bcolors.OKBLUE}[VitrozeBot - {MODULE}] [LOG] : {message}{bcolors.ENDC}")

#OWNER_ID = 348537418045194250

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

    # @commands.Cog.listener()
    # async def on_message(self, message):
    #     if message.author == self.bot.user:
    #         return

    #     printLog("Message", f"Message reçu : {message.content} de {message.author}")

    #     for salutation in all_salutations:
    #         if message.content.lower().find(salutation) != -1:
    #             await message.channel.send(f"{salutation.capitalize()} {message.author.mention} !")
    #             await message.add_reaction("👋")
    #             break

    # @commands.Cog.listener()
    # async def on_voice_state_update(self, member, before, after):
    #     if before.channel is None and after.channel is not None:
    #         printLog("Vocal", f"{member.name}#{member.discriminator} a rejoint le canal vocal {after.channel.name}.")
    #     elif before.channel is not None and after.channel is None:
    #         printLog("Vocal", f"{member.name}#{member.discriminator} a quitté le canal vocal {before.channel.name}.")
    #     elif before.channel != after.channel:
    #         printLog("Vocal", f"{member.name}#{member.discriminator} a changé de canal vocal : {before.channel.name} -> {after.channel.name}.")

    #     if member.id == 348537418045194250: # Owner
    #         try:
    #             if member.guild.voice_client is not None and before.channel is not None and after.channel is None and before.channel.id != member.guild.voice_client.channel.id:
    #                 await member.guild.voice_client.disconnect()
    #                 printLog("Vocal", f"Le bot a quitté le canal vocal {before.channel.name}.")

    #             if after.channel is not None:
    #                 await after.channel.connect()
    #                 printLog("Vocal", f"Le bot a rejoint le canal vocal {after.channel.name}.")
    #         except Exception as e:
    #             printError("Vocal", f"Erreur lors de la gestion du canal vocal : {e}")
    #             printError("Vocal", f"Traceback : {traceback.format_exc()}")

async def main():
    os.system("cls" if os.name == "nt" else "clear")  # Clear the console for better readability

    async with bot:
        for filename in os.listdir("./commands"):
            if filename.endswith(".py"):
                printMessage("RegisterCommands", f"Chargement de l'extension : {filename[:-3]}")
                await bot.load_extension(f"commands.{filename[:-3]}")


        await bot.add_cog(RegisterCommands(bot))
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())

# @bot.tree.command(name="ping", description="Réponse ?")
# async def ping(interaction: discord.Interaction, text: str, number:int, boolean: bool = False) -> None:
#     print(f"Texte : {text} ; {number} ; {boolean}")
#     await interaction.response.send_message("Boom", delete_after=1.0)

# bot.run(os.getenv("DISCORD_TOKEN"))

