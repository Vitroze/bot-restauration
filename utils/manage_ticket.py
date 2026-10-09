import json
import os

import discord
from discord.ext import commands
from .manage_restaurant import get_all_restaurants

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

TYPE_TICKET = {
    "📝 Recrutement": None,
    "❓ Support": None,
}

class TicketSelect(discord.ui.Select):
    def __init__(self, cog: "TicketManager"):
        self.cog = cog
        options = [
            discord.SelectOption(label=name, value=name, description=f"Créer un ticket pour {name}.") for name in TYPE_TICKET.keys()
        ]

        super().__init__(
            placeholder="Choisissez un type de ticket",
            options=options,
            custom_id="ticket_select",
        )

    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        guild = interaction.guild
        member = interaction.user

        await interaction.response.defer(ephemeral=True)

        topic = f"ticket:{member.id}:{ticket_type}"
        existing = discord.utils.get(guild.text_channels, topic=topic)
        if existing:
            await interaction.followup.send(f"Vous avez déjà un ticket ouvert pour {ticket_type} : {existing.mention}", ephemeral=True)
        else:
            category_id = TYPE_TICKET.get(ticket_type)
            category = guild.get_channel(category_id) if category_id else None
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
            }

            channel = await guild.create_text_channel(
                f"ticket-{member.name}-{ticket_type.replace(' ', '-')}",
                topic=topic,
                overwrites=overwrites,
                category=category if isinstance(category, discord.CategoryChannel) else None,
            )


            await channel.send(f"{member.mention}, votre ticket pour {ticket_type} a été créé. Un membre du support vous répondra bientôt.")
            await interaction.followup.send(f"Votre ticket pour {ticket_type} a été créé : {channel.mention}", ephemeral=True)
        await interaction.message.edit(view=TicketView(self.cog))

class TicketView(discord.ui.View):
    def __init__(self, cog: "TicketManager"):
        super().__init__(timeout=None)
        self.add_item(TicketSelect(cog))

class TicketManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_channel: discord.TextChannel | None = None
        self.config_message_id: int | None = None
        self.config_ticket_emoji = "📩"
        self.is_setup_complete = False

    async def cog_load(self):
        self.bot.add_view(TicketView(self))
        await self.load_config_channel()

    def _read_config(self) -> dict:
        if not os.path.exists(CONFIG_FILE):
            return {}
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    def _write_config(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "channel_id": self.config_channel.id,
                    "message_id": self.config_message_id,
                    "ticket_emoji": self.config_ticket_emoji,
                    "type_ticket": TYPE_TICKET
                },
                file, indent=4,
            )

    async def load_config_channel(self):
        await self.bot.wait_until_ready()

        config = self._read_config()
        channel_id = config.get("channel_id")
        message_id = config.get("message_id")
        emoji = config.get("ticket_emoji", "📩")
        if not channel_id or not message_id:
            return

        try:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden):
            print(f"Salon {channel_id} introuvable ou inaccessible.")
            return

        ticket_config = config.get("type_ticket", {})
        if ticket_config:
            for ticket_type, category_id in ticket_config.items():
                if not isinstance(category_id, int) or ticket_type not in TYPE_TICKET:
                    continue

                TYPE_TICKET[ticket_type] = category_id

        self.config_channel = channel
        print(f"Salon de ticket chargé : {channel.name} (ID: {channel.id})")
        self.config_ticket_emoji = emoji
        try:
            await channel.fetch_message(message_id)
            self.config_message_id = message_id
        except discord.NotFound:
            print(f"Message {message_id} introuvable, recréation.")
            await self.send_embed_message(channel)
        except discord.Forbidden:
            print(f"Pas l'accès au message {message_id}.")

    async def _delete_previous_message(self):
        if self.config_channel is None or self.config_message_id is None:
            return
        try:
            message = await self.config_channel.fetch_message(self.config_message_id)
            await message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass

    # ---------- Envoi ----------
    async def send_embed_message(self, channel: discord.TextChannel):
        await self._delete_previous_message()

        embed = discord.Embed(
            title="Système de ticket",
            description=f"Réagissez avec {self.config_ticket_emoji} pour créer un ticket.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="❓ Support", value="Pour toute question ou problème technique.", inline=False)
        embed.add_field(name="💰 Réservation", value="Pour toute demande de réservation dans un restaurant.", inline=False)
        embed.set_footer(text="Merci de votre compréhension.")

        message = await channel.send(embed=embed, view=TicketView(self))

        self.config_channel = channel
        self.config_message_id = message.id
        self._write_config()


    async def setup_config_channel(self, channel: discord.TextChannel):
        self.is_setup_complete = True
        await self.send_embed_message(channel)
        self.is_setup_complete = False

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if self.is_setup_complete:
            return

        if self.config_message_id is None or payload.message_id != self.config_message_id:
            return

        if self.config_channel is not None:
            await self.send_embed_message(self.config_channel)

async def setup(bot):
    await bot.add_cog(TicketManager(bot))