from __future__ import annotations
from typing import TYPE_CHECKING
import inspect
import math
import discord

from models.restaurant import Restaurant
from utils.manage_restaurant import (
    get_all_restaurants,
    save_restaurant,
    delete_restaurant,
    is_existing_restaurant_type,
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

PER_PAGE = 10


async def maybe_await(value):
    """Accepte les fonctions sync ET async (delete_restaurant, par exemple)."""
    if inspect.isawaitable(value):
        return await value
    return value

class EditPermissionRestaurantView(discord.ui.View):
    def __init__(self, parent: "ConfigRestaurantView", restaurant_name: str, guild: discord.Guild, remove: bool = False):
        super().__init__(timeout=120)
        self.parent = parent
        self.restaurant_name = restaurant_name
        self.remove = remove
        self.role_id: int | None = None
        self.permission_id: str | None = None

        # Discord limite un Select à 25 options
        roles = [r for r in guild.roles if r.id != guild.id and not r.managed][-25:]
        role_select = discord.ui.Select(
            placeholder="Sélectionne un rôle...",
            options=[discord.SelectOption(label=r.name[:100], value=str(r.id)) for r in roles],
            row=0,
        )
        role_select.callback = self.on_role
        self.add_item(role_select)

        perm_select = discord.ui.Select(
            placeholder="Sélectionne une permission...",
            options=[
                discord.SelectOption(label=perm_id[:100], value=perm_id, description=desc[:100])
                for perm_id, desc in ALL_TYPES_PERMISSIONS_RESTAURANT.items()
            ],
            row=1,
        )
        perm_select.callback = self.on_perm
        self.add_item(perm_select)

        confirm = discord.ui.Button(
            label="Retirer" if remove else "Ajouter",
            style=discord.ButtonStyle.danger if remove else discord.ButtonStyle.success,
            row=2,
        )
        confirm.callback = self.on_confirm
        self.add_item(confirm)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.parent.author_id

    async def on_role(self, interaction: discord.Interaction):
        self.role_id = int(interaction.data["values"][0])
        await interaction.response.defer()

    async def on_perm(self, interaction: discord.Interaction):
        self.permission_id = interaction.data["values"][0]
        await interaction.response.defer()

    async def on_confirm(self, interaction: discord.Interaction):
        if self.role_id is None or self.permission_id is None:
            await interaction.response.send_message("Choisis un rôle ET une permission.", ephemeral=True)
            return

        restaurant = get_all_restaurants().get(self.restaurant_name)
        if not restaurant:
            await interaction.response.edit_message(content="Ce restaurant n'existe plus.", view=None)
            return

        perms = restaurant.setdefault("permissions", {})
        key = str(self.role_id)

        if self.remove:
            if self.permission_id not in perms.get(key, []):
                await interaction.response.edit_message(content="❌ Cette permission n'est pas configurée pour ce rôle.", view=None)
                return
            perms[key].remove(self.permission_id)
            if not perms[key]:
                del perms[key]
            msg = "✅ Permission supprimée pour le rôle."
        else:
            if self.permission_id in perms.setdefault(key, []):
                await interaction.response.edit_message(content="❌ Cette permission est déjà configurée pour ce rôle.", view=None)
                return
            perms[key].append(self.permission_id)
            msg = "✅ Permission ajoutée pour le rôle."

        await save_restaurant(Restaurant(**restaurant))
        await interaction.response.edit_message(content=msg, view=None)

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
                f"❌ Le type `{new_type}` n'existe pas. Crée-le d'abord avec `/cfg_vresto_create_type`.",
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
        print(f"Erreur modal modification restaurant : {error!r}")
        if interaction.response.is_done():
            await interaction.followup.send("Une erreur est survenue.", ephemeral=True)
        else:
            await interaction.response.send_message("Une erreur est survenue.", ephemeral=True)


class ConfigRestaurantView(discord.ui.View):
    def __init__(self, author_id: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.page = 0
        self.mode = "list"                 # "list" | "detail" | "confirm"
        self.selected: str | None = None   # nom du restaurant sélectionné
        self.message: discord.Message | None = None
        self.rebuild()

    # ---------- Données ----------
    def names(self) -> list[str]:
        return sorted(get_all_restaurants().keys(), key=str.lower)

    def current(self) -> dict | None:
        return get_all_restaurants().get(self.selected) if self.selected else None

    @property
    def page_count(self) -> int:
        return max(1, math.ceil(len(self.names()) / PER_PAGE))

    # ---------- Embeds ----------
    def build_embed(self) -> discord.Embed:
        if self.mode == "list":
            return self.build_list_embed()
        return self.build_detail_embed()

    def build_list_embed(self) -> discord.Embed:
        restaurants = get_all_restaurants()
        names = self.names()
        start = self.page * PER_PAGE
        chunk = names[start:start + PER_PAGE]

        if chunk:
            lines = [
                f"**{start + i + 1}.** {name} • *{restaurants[name].get('type', 'N/A')}*"
                for i, name in enumerate(chunk)
            ]
            description = "\n".join(lines)
        else:
            description = "*Aucun restaurant.*"

        embed = discord.Embed(
            title="Configuration des restaurants",
            description=description,
            color=discord.Color.blue(),
        )
        embed.set_footer(
            text=f"Page {self.page + 1}/{self.page_count} • {len(names)} restaurant(s) • Choisis-en un"
        )
        return embed

    def build_detail_embed(self) -> discord.Embed:
        restaurant = self.current()
        if not restaurant:
            return discord.Embed(title="Restaurant introuvable", color=discord.Color.red())

        color = discord.Color.red() if self.mode == "confirm" else discord.Color.green()
        embed = discord.Embed(
            title=restaurant["name"],
            description=restaurant.get("description") or "*Aucune description.*",
            color=color,
        )
        embed.add_field(name="Type", value=restaurant.get("type", "N/A"), inline=True)
        embed.add_field(name="Localisation", value=restaurant.get("location", "N/A"), inline=True)
        embed.add_field(name="Plats au menu", value=str(len(restaurant.get("menu", []))), inline=True)
        embed.add_field(name="Réservations", value=str(len(restaurant.get("reservations", []))), inline=True)
        embed.add_field(name="Rôles configurés", value=str(len(restaurant.get("permissions", {}))), inline=True)

        if self.mode == "confirm":
            embed.add_field(
                name="⚠️ Suppression",
                value="Cette action est **définitive**. Confirme pour supprimer ce restaurant.",
                inline=False,
            )
        return embed

    # ---------- Composants ----------
    def rebuild(self):
        self.clear_items()
        if self.mode == "list":
            self._add_list_components()
        elif self.mode == "detail":
            self._add_detail_components()
        else:
            self._add_confirm_components()

    def _add_list_components(self):
        names = self.names()
        start = self.page * PER_PAGE
        chunk = names[start:start + PER_PAGE]

        if chunk:
            restaurants = get_all_restaurants()
            select = discord.ui.Select(
                placeholder="Sélectionne un restaurant...",
                options=[
                    discord.SelectOption(
                        label=name[:100],
                        value=name[:100],
                        description=str(restaurants[name].get("type", ""))[:100] or None,
                    )
                    for name in chunk
                ],
                row=0,
            )
            select.callback = self.on_select
            self.add_item(select)

        prev_btn = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.primary,
                                     disabled=self.page == 0, row=1)
        prev_btn.callback = self.on_prev_page
        indicator = discord.ui.Button(label=f"{self.page + 1}/{self.page_count}",
                                      style=discord.ButtonStyle.secondary, disabled=True, row=1)
        next_btn = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.primary,
                                     disabled=self.page >= self.page_count - 1, row=1)
        next_btn.callback = self.on_next_page
        for b in (prev_btn, indicator, next_btn):
            self.add_item(b)

    def _add_detail_components(self):
        edit_btn = discord.ui.Button(label="Modifier", emoji="✏️", style=discord.ButtonStyle.primary)
        edit_btn.callback = self.on_edit

        add_permission = discord.ui.Button(label="Ajouter un rôle", emoji="➕", style=discord.ButtonStyle.success)
        add_permission.callback = self.on_add_permission

        remove_permission = discord.ui.Button(label="Supprimer un rôle", emoji="➖", style=discord.ButtonStyle.danger)
        remove_permission.callback = self.on_remove_permission

        delete_btn = discord.ui.Button(label="Supprimer", emoji="🗑️", style=discord.ButtonStyle.danger)
        delete_btn.callback = self.on_delete

        back_btn = discord.ui.Button(label="Retour à la liste", emoji="📋", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.on_back
        for b in (edit_btn, add_permission, remove_permission, delete_btn, back_btn):
            self.add_item(b)

    def _add_confirm_components(self):
        confirm_btn = discord.ui.Button(label="Confirmer la suppression", emoji="⚠️",
                                        style=discord.ButtonStyle.danger)
        confirm_btn.callback = self.on_confirm_delete
        cancel_btn = discord.ui.Button(label="Annuler", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = self.on_cancel_delete
        for b in (confirm_btn, cancel_btn):
            self.add_item(b)

    async def refresh(self, interaction: discord.Interaction):
        self.rebuild()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_select(self, interaction: discord.Interaction):
        self.selected = interaction.data["values"][0]
        self.mode = "detail"
        await self.refresh(interaction)

    async def on_prev_page(self, interaction: discord.Interaction):
        self.page = max(0, self.page - 1)
        await self.refresh(interaction)

    async def on_next_page(self, interaction: discord.Interaction):
        self.page = min(self.page_count - 1, self.page + 1)
        await self.refresh(interaction)

    async def on_back(self, interaction: discord.Interaction):
        self.mode = "list"
        self.selected = None
        self.page = min(self.page, self.page_count - 1)
        await self.refresh(interaction)

    async def on_edit(self, interaction: discord.Interaction):
        restaurant = self.current()
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return
        await interaction.response.send_modal(EditRestaurantModal(self, restaurant))

    async def on_add_permission(self, interaction: discord.Interaction):
        restaurant = self.current()
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return
        view = EditPermissionRestaurantView(self, restaurant["name"], interaction.guild, remove=False)
        await interaction.response.send_message("Ajouter une permission à un rôle :", view=view, ephemeral=True)

    async def on_remove_permission(self, interaction: discord.Interaction):
        restaurant = self.current()
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return
        view = EditPermissionRestaurantView(self, restaurant["name"], interaction.guild, remove=True)
        await interaction.response.send_message("Retirer une permission à un rôle :", view=view, ephemeral=True)

    async def on_delete(self, interaction: discord.Interaction):
        self.mode = "confirm"
        await self.refresh(interaction)

    async def on_cancel_delete(self, interaction: discord.Interaction):
        self.mode = "detail"
        await self.refresh(interaction)

    async def on_confirm_delete(self, interaction: discord.Interaction):
        name = self.selected
        if name and name in get_all_restaurants():
            await maybe_await(delete_restaurant(name))

        self.mode = "list"
        self.selected = None
        self.page = min(self.page, self.page_count - 1)
        await self.refresh(interaction)
        await interaction.followup.send(f"🗑️ Le restaurant `{name}` a été supprimé.", ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Seul l'auteur de la commande peut utiliser ces boutons.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass