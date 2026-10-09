from __future__ import annotations
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
if TYPE_CHECKING:
    from ui.config_restaurant import ConfigRestaurantView
from utils.manage_restaurant import (
    get_all_restaurants,
    save_restaurant,
)

from ui.base_view import BaseView
from utils.function_utils import format_price
from models.restaurant import Restaurant

class SelectItemView(BaseView):
    """Choix d'un item du menu, pour le modifier ou le supprimer."""
    unauthorized_message = "Seul l'auteur de la commande peut utiliser ceci."
    per_page = 25  # limite Discord pour un Select

    def __init__(self, parent: "ConfigRestaurantView", restaurant_name: str, remove: bool = False):
        super().__init__(parent.author_id, timeout=120)
        self.parent = parent
        self.restaurant_name = restaurant_name
        self.remove = remove
        self.page = 0
        self.rebuild()

    def _menu(self) -> list[dict]:
        restaurant = get_all_restaurants().get(self.restaurant_name) or {}
        return restaurant.get("menu", [])

    def rebuild(self):
        self.clear_items()
        menu = self._menu()
        start = self.page * self.per_page
        chunk = menu[start:start + self.per_page]

        if chunk:
            options = []
            for it in chunk:
                desc = format_price(it.get("price", 0))
                if it.get("description"):
                    desc += f" - {it['description']}"
                options.append(
                    discord.SelectOption(
                        label=it["name"][:100],
                        value=it["name"][:100],
                        description=desc[:100],
                    )
                )
            select = discord.ui.Select(
                placeholder="Sélectionne l'item à supprimer..." if self.remove
                else "Sélectionne l'item à modifier...",
                options=options,
                row=0,
            )
            select.callback = self.on_select
            self.add_item(select)

        if len(menu) > self.per_page:
            prev_btn = discord.ui.Button(label="◀", disabled=self.page == 0, row=1)
            prev_btn.callback = self.on_prev
            next_btn = discord.ui.Button(
                label="▶", disabled=(self.page + 1) * self.per_page >= len(menu), row=1
            )
            next_btn.callback = self.on_next
            self.add_item(prev_btn)
            self.add_item(next_btn)

    async def on_prev(self, interaction: discord.Interaction):
        self.page -= 1
        self.rebuild()
        await interaction.response.edit_message(view=self)

    async def on_next(self, interaction: discord.Interaction):
        self.page += 1
        self.rebuild()
        await interaction.response.edit_message(view=self)

    async def on_select(self, interaction: discord.Interaction):
        item_name = interaction.data["values"][0]
        restaurant = get_all_restaurants().get(self.restaurant_name)
        if not restaurant:
            await interaction.response.edit_message(content="Ce restaurant n'existe plus.", view=None)
            return

        menu = restaurant.get("menu", [])
        item = next((it for it in menu if it["name"][:100] == item_name), None)
        if item is None:
            await interaction.response.edit_message(content="❌ Cet item n'existe plus.", view=None)
            return

        # --- Suppression directe ---
        if self.remove:
            menu.remove(item)
            await save_restaurant(Restaurant(**restaurant))
            self.parent.mode = "detail"
            self.parent.rebuild()
            await self.parent.refresh_message()
            await interaction.response.edit_message(
                content=f"🗑️ Item `{item['name']}` supprimé du menu.", view=None
            )
            return

        # --- Modification : ouvre le modal prérempli ---
        await interaction.response.send_modal(
            EditItem(self.parent, restaurant, edit=True, item=item)
        )

class EditItem(discord.ui.Modal):
    def __init__(
        self,
        view: "ConfigRestaurantView",
        restaurant: dict,
        edit: bool = False,
        item: dict | None = None,
    ):
        super().__init__(title=f"{'Modifier' if edit else 'Ajouter'} un item - {restaurant['name']}"[:45])
        self.config_view = view
        self.restaurant_name = restaurant["name"]
        self.edit = edit
        self.original_name = item["name"] if item else None
        item = item or {}

        self.name = discord.ui.TextInput(
            label="Nom de l'item",
            style=discord.TextStyle.short,
            default=item.get("name") or None,
            max_length=100,
        )
        self.description = discord.ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            default=item.get("description") or None,
            required=False,
            max_length=500,
        )
        self.price = discord.ui.TextInput(
            label="Prix",
            style=discord.TextStyle.short,
            placeholder="Exemple : 9.99",
            default=str(item["price"]) if "price" in item else None,
            max_length=10,
        )
        self.picture = discord.ui.TextInput(
            label="URL de l'image (optionnel)",
            style=discord.TextStyle.short,
            placeholder="Exemple : https://example.com/image.png",
            default=item.get("picture") or None,
            required=False,
            max_length=200,
        )
        for it in (self.name, self.description, self.price, self.picture):
            self.add_item(it)

    async def on_submit(self, interaction: discord.Interaction):
        restaurant = get_all_restaurants().get(self.restaurant_name)
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return

        item_name = self.name.value.strip()
        if not item_name:
            await interaction.response.send_message("❌ Le nom de l'item ne peut pas être vide.", ephemeral=True)
            return

        try:
            price = float(self.price.value.strip().replace(",", "."))
            if price < 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Le prix doit être un nombre positif.", ephemeral=True)
            return

        item = {
            "name": item_name,
            "description": self.description.value.strip(),
            "price": price,
            "picture": self.picture.value.strip() or None,
        }

        menu = restaurant.setdefault("menu", [])
        if self.edit:
            index = next(
                (i for i, it in enumerate(menu) if it["name"] == self.original_name), None
            )
            if index is None:
                await interaction.response.send_message("❌ L'item n'existe plus dans le menu.", ephemeral=True)
                return
            if item_name != self.original_name and any(it["name"] == item_name for it in menu):
                await interaction.response.send_message("❌ Un item avec ce nom existe déjà dans le menu.", ephemeral=True)
                return
            menu[index] = item
        else:
            if any(it["name"] == item_name for it in menu):
                await interaction.response.send_message("❌ Un item avec ce nom existe déjà dans le menu.", ephemeral=True)
                return
            menu.append(item)

        await save_restaurant(Restaurant(**restaurant))

        view = self.config_view
        view.mode = "detail"
        view.rebuild()

        if self.edit:
            # Le modal vient du message éphémère de sélection : on met à jour
            # le message de config, puis on remplace l'éphémère par une confirmation.
            await view.refresh_message()
            await interaction.response.edit_message(
                content=f"✅ Item `{item_name}` modifié.", view=None
            )
        else:
            await interaction.response.edit_message(embed=view.build_embed(), view=view)
            await interaction.followup.send("✅ Item ajouté au menu.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        if interaction.response.is_done():
            await interaction.followup.send("Une erreur est survenue.", ephemeral=True)
        else:
            await interaction.response.send_message("Une erreur est survenue.", ephemeral=True)