from __future__ import annotations

import inspect

import discord

from ui.base_view import PaginatedView
from ui.category_restaurant_view import CategoryRestaurantView
from ui.config_restaurant_embeds import ConfigRestaurantEmbedsMixin
from ui.edit_item import EditItem, SelectItemView
from ui.edit_restaurant import EditPermissionRestaurantView, EditRestaurantModal
from utils.manage_permission import check_ui_permission, ensure_ui_permission
from utils.manage_restaurant import (
    delete_restaurant,
    get_all_restaurants,
)


async def maybe_await(value):
    """Accepte les fonctions sync ET async (delete_restaurant, par exemple)."""
    if inspect.isawaitable(value):
        return await value
    return value


class ConfigRestaurantView(ConfigRestaurantEmbedsMixin, PaginatedView):
    per_page = 10

    def __init__(self, author_id: int, timeout: float = 300):
        super().__init__(author_id, timeout)
        self.mode = "list"  # "list" | "detail" | "confirm"
        self.selected: str | None = None  # nom du restaurant sélectionné
        self.rebuild()

    # ---------- Données ----------
    def names(self) -> list[str]:
        return sorted(get_all_restaurants().keys(), key=str.lower)

    def current(self) -> dict | None:
        return get_all_restaurants().get(self.selected) if self.selected else None

    def total_items(self) -> int:
        return len(self.names())

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
        restaurants = get_all_restaurants()
        _, chunk = self.page_slice(self.names())

        if chunk:
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

        self.add_pagination_buttons(row=1)

    def _add_detail_components(self):
        edit_btn = discord.ui.Button(
            label="Modifier", emoji="✏️", style=discord.ButtonStyle.primary
        )
        edit_btn.callback = self.on_edit

        add_permission = discord.ui.Button(
            label="Ajouter un rôle", emoji="➕", style=discord.ButtonStyle.success
        )
        add_permission.callback = self.on_add_permission

        remove_permission = discord.ui.Button(
            label="Supprimer un rôle", emoji="➖", style=discord.ButtonStyle.danger
        )
        remove_permission.callback = self.on_remove_permission

        delete_btn = discord.ui.Button(
            label="Supprimer", emoji="🗑️", style=discord.ButtonStyle.danger
        )
        delete_btn.callback = self.on_delete

        config_category_btn = discord.ui.Button(
            label="Configurer la catégorie", emoji="🏷️", style=discord.ButtonStyle.secondary
        )
        config_category_btn.callback = self.on_config_category

        add_item_btn = discord.ui.Button(
            label="Ajouter un objet au menu", emoji="🍽️", style=discord.ButtonStyle.success
        )
        add_item_btn.callback = self.on_add_item

        modify_item_btn = discord.ui.Button(
            label="Modifier un objet du menu", emoji="✏️", style=discord.ButtonStyle.primary
        )
        modify_item_btn.callback = self.on_modify_item

        remove_item_btn = discord.ui.Button(
            label="Supprimer un objet du menu", emoji="🗑️", style=discord.ButtonStyle.danger
        )
        remove_item_btn.callback = self.on_remove_item

        back_btn = discord.ui.Button(
            label="Retour à la liste", emoji="📋", style=discord.ButtonStyle.secondary
        )
        back_btn.callback = self.on_back
        for b in (
            edit_btn,
            add_permission,
            remove_permission,
            delete_btn,
            config_category_btn,
            add_item_btn,
            modify_item_btn,
            remove_item_btn,
            back_btn,
        ):
            self.add_item(b)

    def _add_confirm_components(self):
        confirm_btn = discord.ui.Button(
            label="Confirmer la suppression", emoji="⚠️", style=discord.ButtonStyle.danger
        )
        confirm_btn.callback = self.on_confirm_delete
        cancel_btn = discord.ui.Button(label="Annuler", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = self.on_cancel_delete
        for b in (confirm_btn, cancel_btn):
            self.add_item(b)

    # ---------- Callbacks ----------
    async def on_select(self, interaction: discord.Interaction):
        restaurant_name = interaction.data["values"][0]
        if not await ensure_ui_permission(interaction, restaurant_name, "view_config"):
            return
        self.selected = restaurant_name
        self.mode = "detail"
        await self.refresh(interaction)

    async def on_back(self, interaction: discord.Interaction):
        self.mode = "list"
        self.selected = None
        self.clamp_page()
        await self.refresh(interaction)

    @check_ui_permission("edit_restaurant", restaurant_attr="selected")
    async def on_edit(self, interaction: discord.Interaction):
        restaurant = self.current()
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return
        await interaction.response.send_modal(EditRestaurantModal(self, restaurant))

    @check_ui_permission("manage_permissions", restaurant_attr="selected")
    async def on_add_permission(self, interaction: discord.Interaction):
        restaurant = self.current()
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return

        view = EditPermissionRestaurantView(
            self, restaurant["name"], interaction.guild, remove=False
        )
        if not view.available_roles():
            await interaction.response.send_message(
                "Tous les rôles ont déjà toutes les permissions.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            "Ajouter une permission à un rôle :", view=view, ephemeral=True
        )

    @check_ui_permission("manage_permissions", restaurant_attr="selected")
    async def on_remove_permission(self, interaction: discord.Interaction):
        restaurant = self.current()
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return

        view = EditPermissionRestaurantView(
            self, restaurant["name"], interaction.guild, remove=True
        )
        if not view.available_roles():
            await interaction.response.send_message(
                "Aucun rôle n'a de permission configurée.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            "Retirer une permission à un rôle :", view=view, ephemeral=True
        )

    @check_ui_permission("edit_restaurant", restaurant_attr="selected")
    async def on_delete(self, interaction: discord.Interaction):
        self.mode = "confirm"
        await self.refresh(interaction)

    async def on_cancel_delete(self, interaction: discord.Interaction):
        self.mode = "detail"
        await self.refresh(interaction)

    @check_ui_permission("edit_restaurant", restaurant_attr="selected")
    async def on_confirm_delete(self, interaction: discord.Interaction):
        name = self.selected
        if name and name in get_all_restaurants():
            await maybe_await(delete_restaurant(name))

        self.mode = "list"
        self.selected = None
        self.clamp_page()
        await self.refresh(interaction)
        await interaction.followup.send(
            f"🗑️ Le restaurant `{name}` a été supprimé.", ephemeral=True
        )

    @check_ui_permission("edit_restaurant", restaurant_attr="selected")
    async def on_config_category(self, interaction: discord.Interaction):
        restaurant = self.current()
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return

        view = CategoryRestaurantView(self, restaurant["name"], interaction.guild)
        category_id = restaurant.get("category_id")
        if category_id is not None:
            view.category_id = category_id
        await interaction.response.send_message(
            "Sélectionne la catégorie dans laquelle les salons du restaurant seront créés :",
            view=view,
            ephemeral=True,
        )

    @check_ui_permission("add_item_menu", restaurant_attr="selected")
    async def on_add_item(self, interaction: discord.Interaction):
        restaurant = self.current()
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return

        await interaction.response.send_modal(EditItem(self, restaurant, edit=False))

    @check_ui_permission("edit_item_menu", restaurant_attr="selected")
    async def on_modify_item(self, interaction: discord.Interaction):
        restaurant = self.current()
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return
        if not restaurant.get("menu"):
            await interaction.response.send_message(
                "❌ Le menu de ce restaurant est vide.", ephemeral=True
            )
            return

        view = SelectItemView(self, restaurant["name"], remove=False)
        await interaction.response.send_message(
            "Sélectionne l'item à modifier :", view=view, ephemeral=True
        )

    @check_ui_permission("remove_item_menu", restaurant_attr="selected")
    async def on_remove_item(self, interaction: discord.Interaction):
        restaurant = self.current()
        if not restaurant:
            await interaction.response.send_message("Ce restaurant n'existe plus.", ephemeral=True)
            return
        if not restaurant.get("menu"):
            await interaction.response.send_message(
                "❌ Le menu de ce restaurant est vide.", ephemeral=True
            )
            return

        view = SelectItemView(self, restaurant["name"], remove=True)
        await interaction.response.send_message(
            "Sélectionne l'item à supprimer :", view=view, ephemeral=True
        )
