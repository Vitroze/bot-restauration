import discord

from models.restaurant import Restaurant
from ui.base_view import BaseView
from ui.config_restaurant import ConfigRestaurantView
from utils.manage_restaurant import get_all_restaurants, save_restaurant


class CategoryRestaurantView(BaseView):
    unauthorized_message = "Seul l'auteur de la commande peut utiliser ceci."

    def __init__(self, parent: "ConfigRestaurantView", restaurant_name: str, guild: discord.Guild):
        super().__init__(parent.author_id, timeout=120)
        self.parent = parent
        self.restaurant_name = restaurant_name
        self.guild = guild
        self.category_id: int | None = None
        self.rebuild()

    # ---------- Composants ----------
    def rebuild(self):
        self.clear_items()

        category_select = discord.ui.ChannelSelect(
            placeholder="Sélectionne une catégorie...",
            channel_types=[discord.ChannelType.category],
            default_values=(
                [discord.Object(id=self.category_id, type=discord.CategoryChannel)]
                if self.category_id is not None
                else []
            ),
            row=0,
        )
        category_select.callback = self.on_category
        self.add_item(category_select)

        confirm_btn = discord.ui.Button(
            label="Confirmer",
            style=discord.ButtonStyle.success,
            disabled=self.category_id is None,
            row=1,
        )
        confirm_btn.callback = self.on_confirm
        self.add_item(confirm_btn)

    # ---------- Callbacks ----------
    async def on_category(self, interaction: discord.Interaction):
        category_id = int(interaction.data["values"][0])
        self.category_id = category_id
        self.rebuild()
        await interaction.response.edit_message(view=self)

    async def on_confirm(self, interaction: discord.Interaction):
        restaurant = get_all_restaurants().get(self.restaurant_name)
        if not restaurant:
            await interaction.response.edit_message(
                content="Ce restaurant n'existe plus.", view=None
            )
            return

        restaurant["category_id"] = self.category_id
        await save_restaurant(Restaurant(**restaurant))
        await self.parent.refresh_message()

        self.category_id = None
        self.rebuild()
        await interaction.response.edit_message(
            content=f"✅ Catégorie configurée pour le restaurant `{self.restaurant_name}`.",
            view=self.parent,
        )
