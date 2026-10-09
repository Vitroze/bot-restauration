import discord
import asyncio

class OrderView(discord.ui.View):
    def __init__(self, customer_id: int, chef_role_ids: list[int]):
        super().__init__(timeout=None)
        self.customer_id = customer_id
        self.chef_role_ids = chef_role_ids
        self.taken_by: discord.abc.User | None = None

    # Seuls les chefs (et les admins) peuvent utiliser les boutons
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        member = interaction.user
        is_chef = isinstance(member, discord.Member) and (
            member.guild_permissions.administrator
            or any(role.id in self.chef_role_ids for role in member.roles)
        )
        if not is_chef:
            await interaction.response.send_message(
                "Seul le chef peut utiliser ces boutons.", ephemeral=True
            )
        return is_chef

    @discord.ui.button(label="Prendre la commande", emoji="👨‍🍳", style=discord.ButtonStyle.success)
    async def take_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.taken_by:
            await interaction.response.send_message(
                f"Déjà prise en charge par {self.taken_by.mention}.", ephemeral=True
            )
            return

        if not isinstance(interaction.user, discord.Member) or not (
            interaction.user.guild_permissions.administrator
            or any(role.id in self.chef_role_ids for role in interaction.user.roles)
        ):
            await interaction.response.send_message(
                "Seul le chef peut prendre la commande.", ephemeral=True
            )
            return

        self.taken_by = interaction.user

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.orange()
        embed.add_field(name="Pris en charge par", value=interaction.user.mention, inline=False)

        button.disabled = True
        button.label = "Commande prise"

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.channel.send(
            f"✅ <@{self.customer_id}>, ta commande est prise en charge par {interaction.user.mention} !",
            allowed_mentions=discord.AllowedMentions(users=True),
        )

    @discord.ui.button(label="Fermer la commande", emoji="🔒", style=discord.ButtonStyle.danger)
    async def close_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.dark_grey()
        embed.add_field(name="Statut", value=f"Fermée par {interaction.user.mention}", inline=False)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

        await interaction.channel.send("🔒 Commande terminée. Ce salon sera supprimé dans 10 secondes.")

        # Prévient le client en MP (peut échouer si ses MP sont fermés)
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