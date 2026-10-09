from __future__ import annotations
from typing import TYPE_CHECKING

import discord

from models.restaurant import Restaurant
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
