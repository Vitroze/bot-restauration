from __future__ import annotations

import re
import traceback
from typing import TYPE_CHECKING

import discord

from ui.order_ticket import OrderView
from utils.function_utils import format_price, get_role_chef
from utils.logger import print_error

if TYPE_CHECKING:
    from ui.menu import MenuUI


def slugify(text: str) -> str:
    """Convertit un texte en un slug utilisable pour les noms de salons Discord."""

    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:30] or "client"


class CheckoutModal(discord.ui.Modal):
    def __init__(self, view: "MenuUI"):
        super().__init__(title=f"Paiement - {format_price(view.cart_total())}"[:45])
        self.menu_view = view

        self.nom = discord.ui.TextInput(
            label="Nom de la commande",
            placeholder="Ex : Dupont",
            max_length=50,
        )
        self.lieu = discord.ui.TextInput(
            label="Table ou adresse de livraison",
            placeholder="Ex : Table 4",
            max_length=100,
        )
        self.remarque = discord.ui.TextInput(
            label="Remarque (optionnel)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=300,
        )
        for item in (self.nom, self.lieu, self.remarque):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        view = self.menu_view
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "Commande impossible en message privé.", ephemeral=True
            )
            return
        if not view.cart:
            await interaction.response.send_message("Ton panier est vide.", ephemeral=True)
            return

        await interaction.response.defer()

        chef_roles = get_role_chef(view.restaurant, guild)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True
            ),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        for role in chef_roles:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        category_id = getattr(view.restaurant, "category_id", None)
        category = guild.get_channel(category_id) if category_id else None
        sID = f"commande-{slugify(interaction.user.name)}"
        existing_channel = discord.utils.get(guild.text_channels, name=sID, category=category)

        if existing_channel:
            await interaction.followup.send(
                f"❌ Tu as déjà une commande en cours : {existing_channel.mention}",
                ephemeral=True,
            )
            return

        try:
            channel = await guild.create_text_channel(
                name=sID,
                category=category,
                overwrites=overwrites,
                topic=f"Commande de {interaction.user} - {view.restaurant.name}",
                reason="Nouvelle commande",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Je n'ai pas la permission de créer un salon (il me faut « Gérer les salons »).",
                ephemeral=True,
            )
            return
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ Impossible de créer le salon : {e}", ephemeral=True
            )
            return

        recap = discord.Embed(
            title=f"🧾 Nouvelle commande - {view.restaurant.name}",
            description="\n".join(view.cart_lines()),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        recap.add_field(name="Total", value=format_price(view.cart_total()), inline=True)
        recap.add_field(name="Nom", value=self.nom.value, inline=True)
        recap.add_field(name="Client", value=interaction.user.mention, inline=True)
        recap.add_field(name="Lieu", value=self.lieu.value, inline=False)
        if self.remarque.value:
            recap.add_field(name="Remarque", value=self.remarque.value, inline=False)

        chefs = (
            " ".join(r.mention for r in chef_roles) or "*Aucun chef configuré pour ce restaurant*"
        )
        order_view = OrderView(interaction.user.id, view.restaurant.name)
        await channel.send(
            content=f"👨‍🍳 {chefs} - nouvelle commande de {interaction.user.mention} !",
            embed=recap,
            view=order_view,
            allowed_mentions=discord.AllowedMentions(users=True, roles=True),
        )

        view.cart.clear()
        view.detail_index = None
        view.rebuild()
        await interaction.edit_original_response(embed=view.build_embed(), view=view)
        await interaction.followup.send(
            f"✅ Commande envoyée ! Suis-la ici : {channel.mention}", ephemeral=True
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print_error("Checkout", f"Erreur modal paiement : {error!r}")
        print_error("Checkout", f"Traceback : {traceback.format_exc()}")
        if interaction.response.is_done():
            await interaction.followup.send("Une erreur est survenue.", ephemeral=True)
        else:
            await interaction.response.send_message("Une erreur est survenue.", ephemeral=True)
