from pyexpat.errors import messages

import discord
from discord import app_commands
from discord.ext import commands
from main import printMessage

printMessage("Config", "Chargement de l'extension : config")

PREFIX = "config_"

@app_commands.guild_only()
class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # TODO: Rework system

    @app_commands.command(name=f"{PREFIX}set_permission", description="Définit les permissions pour un rôle spécifique.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_permission(self, interaction: discord.Interaction, role: discord.Role, permission: str):
        await interaction.response.send_message(f"Les permissions pour le rôle '{role.name}' ont été définies.", ephemeral=True)

    @app_commands.command(name=f"{PREFIX}add_item", description="Ajoute un item à la liste des items.")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_item(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.send_message(f"L'item '{item_name}' a été ajouté à la liste des items.", ephemeral=True)
    # @app_commands.command(name="kick", description="Expulse un membre du serveur.")
    # @app_commands.checks.has_permissions(kick_members=True)
    # async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
    #     if not interaction.user.guild_permissions.kick_members:
    #         await interaction.response.send_message("Vous n'avez pas la permission d'expulser des membres.", ephemeral=True)
    #         return

    #     if member == interaction.user:
    #         await interaction.response.send_message("Vous ne pouvez pas vous expulser vous-même.", ephemeral=True)
    #         return

    #     if member == self.bot.user:
    #         await interaction.response.send_message("Je ne peux pas m'expulser moi-même.", ephemeral=True)
    #         return

    #     await member.send(f"Vous avez été expulsé du serveur {interaction.guild.name} par {interaction.user.name}. Raison : {reason}")
    #     await member.kick(reason=reason)
    #     await interaction.response.send_message(f"{member.mention} a été expulsé du serveur.\n> Raison : {reason}")

async def setup(bot):
    await bot.add_cog(Config(bot))