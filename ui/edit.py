from __future__ import annotations
from typing import TYPE_CHECKING

import discord

from models.restaurant import Restaurant
from utils.function_utils import format_price
from ui.base_view import BaseView
if TYPE_CHECKING:
    from ui.config_restaurant import ConfigRestaurantView
from utils.manage_restaurant import (
    get_all_restaurants,
    is_existing_restaurant_type,
    save_restaurant,
)

ALL_TYPES_PERMISSIONS_RESTAURANT = {
    "edit_restaurant": "Modifier les informations du restaurant",
    "view_config": "Voir la configuration du restaurant",
    "manage_reservations": "Gérer les réservations du restaurant",
    "see_reservations": "Voir les réservations du restaurant",
    "manage_tickets": "Gérer les tickets du restaurant",
    "add_item_menu": "Ajouter un item au menu d'un restaurant",
    "edit_item_menu": "Modifier un item du menu d'un restaurant",
    "remove_item_menu": "Supprimer un item du menu d'un restaurant",
    "take_command": "Prendre une commande dans le restaurant",
}


class EditPermissionRestaurantView(BaseView):
    unauthorized_message = "Seul l'auteur de la commande peut utiliser ceci."

    def __init__(
        self,
        parent: "ConfigRestaurantView",
        restaurant_name: str,
        guild: discord.Guild,
        remove: bool = False,
    ):
        super().__init__(parent.author_id, timeout=120)
        self.parent = parent
        self.restaurant_name = restaurant_name
        self.guild = guild
        self.remove = remove
        self.role_id: int | None = None
        self.permission_id: str | None = None
        self.rebuild()

    # ---------- Données ----------
    def _configured(self) -> dict:
        restaurant = get_all_restaurants().get(self.restaurant_name) or {}
        return restaurant.get("permissions", {})

    def available_roles(self) -> list[discord.Role]:
        configured = self._configured()
        total = len(ALL_TYPES_PERMISSIONS_RESTAURANT)
        roles = []
        for role in reversed(self.guild.roles):
            if role.is_default():
                continue

            role_perms = configured.get(role.id, [])
            if self.remove:
                if role_perms:
                    roles.append(role)
            else:
                if not role.managed and len(role_perms) < total:
                    roles.append(role)
        return roles

    def available_permissions(self) -> list[str]:
        if self.role_id is None:
            return []
        role_perms = self._configured().get(self.role_id, [])
        if self.remove:
            return [p for p in ALL_TYPES_PERMISSIONS_RESTAURANT if p in role_perms]
        return [p for p in ALL_TYPES_PERMISSIONS_RESTAURANT if p not in role_perms]

    # ---------- Composants ----------
    def rebuild(self):
        self.clear_items()

        role_select = discord.ui.RoleSelect(
            placeholder="Sélectionne un rôle...",
            default_values=(
                [discord.Object(id=self.role_id, type=discord.Role)]
                if self.role_id is not None
                else []
            ),
            row=0,
        )
        role_select.callback = self.on_role
        self.add_item(role_select)

        if self.role_id is not None:
            perm_select = discord.ui.Select(
                placeholder="Sélectionne une permission...",
                options=[
                    discord.SelectOption(
                        label=perm_id[:100],
                        value=perm_id,
                        description=ALL_TYPES_PERMISSIONS_RESTAURANT[perm_id][:100],
                        default=(perm_id == self.permission_id),
                    )
                    for perm_id in self.available_permissions()
                ],
                row=1,
            )
            perm_select.callback = self.on_perm
            self.add_item(perm_select)

        confirm = discord.ui.Button(
            label="Retirer" if self.remove else "Ajouter",
            style=discord.ButtonStyle.danger if self.remove else discord.ButtonStyle.success,
            disabled=self.role_id is None or self.permission_id is None,
            row=2,
        )
        confirm.callback = self.on_confirm
        self.add_item(confirm)

    # ---------- Callbacks ----------
    async def on_role(self, interaction: discord.Interaction):
        role_id = int(interaction.data["values"][0])
        self.role_id = role_id
        self.permission_id = None
        if not self.available_permissions():
            self.role_id = None
            self.rebuild()
            msg = (
                "Ce rôle n'a aucune permission configurée."
                if self.remove
                else "Ce rôle a déjà toutes les permissions."
            )
            await interaction.response.edit_message(content=f"❌ {msg}", view=self)
            return
        self.rebuild()
        await interaction.response.edit_message(content=None, view=self)

    async def on_perm(self, interaction: discord.Interaction):
        self.permission_id = interaction.data["values"][0]
        self.rebuild()
        await interaction.response.edit_message(view=self)

    async def on_confirm(self, interaction: discord.Interaction):
        restaurant = get_all_restaurants().get(self.restaurant_name)
        if not restaurant:
            await interaction.response.edit_message(
                content="Ce restaurant n'existe plus.", view=None
            )
            return

        perms = restaurant.setdefault("permissions", {})
        key = self.role_id

        if self.remove:
            if self.permission_id in perms.get(key, []):
                perms[key].remove(self.permission_id)
                if not perms[key]:
                    del perms[key]
            msg = f"✅ Permission `{self.permission_id}` retirée pour <@&{self.role_id}>."
        else:
            role_perms = perms.setdefault(key, [])
            if self.permission_id not in role_perms:
                role_perms.append(self.permission_id)
            msg = f"✅ Permission `{self.permission_id}` ajoutée pour <@&{self.role_id}>."

        await save_restaurant(Restaurant(**restaurant))
        await self.parent.refresh_message()

        self.role_id = None
        self.permission_id = None

        if not self.available_roles():
            end = (
                "Plus aucun rôle à retirer."
                if self.remove
                else "Tous les rôles ont déjà toutes les permissions."
            )
            await interaction.response.edit_message(content=f"{msg}\n{end}", view=None)
            return

        self.rebuild()
        await interaction.response.edit_message(content=msg, view=self)


class EditRestaurantModal(discord.ui.Modal):
    def __init__(self, view: "ConfigRestaurantView", restaurant: dict):
        super().__init__(title=f"Modifier {restaurant['name']}"[:45])
        self.config_view = view
        self.restaurant_name = restaurant["name"]

        self.description = discord.ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            default=restaurant.get("description", ""),
            max_length=500,
        )
        self.type_restaurant = discord.ui.TextInput(
            label="Type de restaurant",
            default=restaurant.get("type", ""),
            max_length=50,
        )
        self.location = discord.ui.TextInput(
            label="Localisation",
            default=restaurant.get("location", ""),
            max_length=100,
        )
        for item in (self.description, self.type_restaurant, self.location):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        restaurant = get_all_restaurants().get(self.restaurant_name)
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return

        new_type = self.type_restaurant.value.strip()
        if not is_existing_restaurant_type(new_type):
            await interaction.response.send_message(
                f"❌ Le type `{new_type}` n'existe pas. "
                f"Crée-le d'abord avec `/cfg_create_type`.",
                ephemeral=True,
            )
            return

        restaurant["description"] = self.description.value
        restaurant["type"] = new_type
        restaurant["location"] = self.location.value
        await save_restaurant(Restaurant(**restaurant))

        view = self.config_view
        view.mode = "detail"
        view.rebuild()
        await interaction.response.edit_message(embed=view.build_embed(), view=view)
        await interaction.followup.send("✅ Restaurant modifié.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        if interaction.response.is_done():
            await interaction.followup.send("Une erreur est survenue.", ephemeral=True)
        else:
            await interaction.response.send_message("Une erreur est survenue.", ephemeral=True)

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