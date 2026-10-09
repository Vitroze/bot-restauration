import traceback

import discord
import asyncio
from utils.function_utils import get_role_chef
from utils.manage_restaurant import get_restaurant_by_name

def _is_chef(interaction: discord.Interaction, restaurant_id: str) -> bool:
    member = interaction.user
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    restaurant = get_restaurant_by_name(restaurant_id)
    if restaurant is None:
        return False
    roles = get_role_chef(restaurant, interaction.guild)
    return any(r in roles for r in member.roles)

class TakeOrderButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"order:take:(?P<customer_id>\d+):(?P<restaurant_id>[^:]+)",
):
    def __init__(self, customer_id: int, restaurant_id: str, *, taken: bool = False):
        super().__init__(discord.ui.Button(
            label="Commande prise" if taken else "Prendre la commande",
            emoji="👨‍🍳",
            style=discord.ButtonStyle.success,
            custom_id=f"order:take:{customer_id}:{restaurant_id}",
            disabled=taken,
        ))
        self.customer_id = customer_id
        self.restaurant_id = restaurant_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["customer_id"]), match["restaurant_id"])

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        try:
            ok = _is_chef(interaction, self.restaurant_id)
        except Exception as e:
            ok = False
        if not ok:
            await interaction.response.send_message("Seul le chef peut utiliser ces boutons.", ephemeral=True)
        return ok

    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.orange()
        embed.add_field(name="Pris en charge par", value=interaction.user.mention, inline=False)

        view = discord.ui.View(timeout=None)
        view.add_item(TakeOrderButton(self.customer_id, self.restaurant_id, taken=True))
        view.add_item(CloseOrderButton(self.customer_id, self.restaurant_id))

        await interaction.response.edit_message(embed=embed, view=view)
        await interaction.channel.send(
            f"✅ <@{self.customer_id}>, ta commande est prise en charge par {interaction.user.mention} !",
            allowed_mentions=discord.AllowedMentions(users=True),
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(f"❌ Une erreur est survenue : {error}", ephemeral=True)


class CloseOrderButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"order:close:(?P<customer_id>\d+):(?P<restaurant_id>[^:]+)",
):
    def __init__(self, customer_id: int, restaurant_id: str):
        super().__init__(discord.ui.Button(
            label="Fermer la commande",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id=f"order:close:{customer_id}:{restaurant_id}",
        ))
        self.customer_id = customer_id
        self.restaurant_id = restaurant_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["customer_id"]), match["restaurant_id"])

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not _is_chef(interaction, self.restaurant_id):
            await interaction.response.send_message("Seul le chef peut utiliser ces boutons.", ephemeral=True)
            return False
        return True

    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.dark_grey()
        embed.add_field(name="Statut", value=f"Fermée par {interaction.user.mention}", inline=False)

        view = discord.ui.View.from_message(interaction.message)
        for child in view.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=view)

        await interaction.channel.send("🔒 Commande terminée. Ce salon sera supprimé dans 10 secondes.")

        customer = interaction.guild.get_member(self.customer_id)
        if customer:
            try:
                await customer.send(f"🔒 Ta commande chez **{embed.title.split(' - ')[-1]}** est terminée. Merci !")
            except discord.HTTPException:
                pass

        await asyncio.sleep(10)
        try:
            await interaction.channel.delete(reason=f"Commande fermée par {interaction.user}")
        except discord.HTTPException:
            pass

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(f"❌ Une erreur est survenue : {error}", ephemeral=True)

class OrderView(discord.ui.View):
    def __init__(self, customer_id: int, restaurant_id: str):
        super().__init__(timeout=None)
        self.add_item(TakeOrderButton(customer_id, restaurant_id))
        self.add_item(CloseOrderButton(customer_id, restaurant_id))