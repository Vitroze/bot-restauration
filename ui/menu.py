import discord

from ui.base_view import PaginatedView
from ui.checkout import CheckoutModal
from utils.function_utils import format_price, to_float


class MenuUI(PaginatedView):
    per_page = 5
    unauthorized_message = (
        "Seul l'auteur de la commande peut naviguer. Utilise `/menu` pour avoir le tien."
    )

    def __init__(self, restaurant, menu_items: list[dict], author_id: int, timeout: float = 300):
        super().__init__(author_id, timeout)
        self.restaurant = restaurant
        self.menu_items = menu_items
        self.detail_index: int | None = None  # None = mode liste
        self.cart: dict[int, int] = {}  # index du plat -> quantité
        self.rebuild()

    def total_items(self) -> int:
        return len(self.menu_items)

    def cart_total(self) -> float:
        return sum(to_float(self.menu_items[i].get("price")) * qty for i, qty in self.cart.items())

    def cart_count(self) -> int:
        return sum(self.cart.values())

    def cart_lines(self) -> list[str]:
        return [
            f"{qty}× {self.menu_items[i].get('name', 'Sans nom')} - "
            f"{format_price(to_float(self.menu_items[i].get('price')) * qty)}"
            for i, qty in self.cart.items()
        ]

    # ---------- Embeds ----------
    def build_embed(self) -> discord.Embed:
        return self.build_list_embed() if self.detail_index is None else self.build_detail_embed()

    def build_list_embed(self) -> discord.Embed:
        start, chunk = self.page_slice(self.menu_items)
        lines = [
            f"**{start + i + 1}.** {item.get('name', 'Sans nom')}" for i, item in enumerate(chunk)
        ]

        embed = discord.Embed(
            title=f"Menu de {self.restaurant.name}",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )

        # Tableau du panier sous le menu
        if self.cart:
            cart_text = "\n".join(self.cart_lines())
            if len(cart_text) > 900:
                cart_text = cart_text[:900] + "\n…"
            embed.add_field(
                name=f"🛒 Votre panier ({self.cart_count()})", value=cart_text, inline=False
            )
            embed.add_field(
                name="Total", value=f"**{format_price(self.cart_total())}**", inline=False
            )
        else:
            embed.add_field(name="🛒 Votre panier", value="*Vide*", inline=False)

        embed.set_footer(
            text=f"Page {self.page + 1}/{self.page_count} • Choisis un plat pour voir le détail"
        )
        return embed

    def build_detail_embed(self) -> discord.Embed:
        item = self.menu_items[self.detail_index]
        embed = discord.Embed(
            title=item.get("name", "Sans nom"),
            description=item.get("description") or "*Aucune description.*",
            color=discord.Color.green(),
        )
        embed.set_author(name=f"Menu de {self.restaurant.name}")
        embed.add_field(name="Prix", value=format_price(item.get("price", "?")), inline=True)
        embed.add_field(
            name="Dans le panier", value=str(self.cart.get(self.detail_index, 0)), inline=True
        )

        if item.get("picture"):
            embed.set_image(url=item["picture"])
        embed.set_footer(text=f"Plat {self.detail_index + 1}/{len(self.menu_items)}")
        return embed

    # ---------- Composants ----------
    def rebuild(self):
        self.clear_items()
        if self.detail_index is None:
            self._add_list_components()
        else:
            self._add_detail_components()

    def _add_list_components(self):
        start, chunk = self.page_slice(self.menu_items)

        select = discord.ui.Select(
            placeholder="Voir le détail d'un plat...",
            options=[
                discord.SelectOption(
                    label=item.get("name", "Sans nom")[:100],
                    value=str(start + i),
                    description=format_price(item.get("price", "?")),
                )
                for i, item in enumerate(chunk)
            ],
            row=0,
        )
        select.callback = self.on_select
        self.add_item(select)

        self.add_pagination_buttons(row=1)

        pay_btn = discord.ui.Button(
            label="Payer",
            emoji="💳",
            style=discord.ButtonStyle.success,
            disabled=not self.cart,
            row=2,
        )
        pay_btn.callback = self.on_pay
        clear_btn = discord.ui.Button(
            label="Vider le panier",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            disabled=not self.cart,
            row=2,
        )
        clear_btn.callback = self.on_clear
        for b in (pay_btn, clear_btn):
            self.add_item(b)

    def _add_detail_components(self):
        qty = self.cart.get(self.detail_index, 0)

        prev_btn = discord.ui.Button(
            emoji="◀️",
            label="Plat précédent",
            style=discord.ButtonStyle.secondary,
            disabled=self.detail_index == 0,
            row=0,
        )
        prev_btn.callback = self.on_prev_item
        back_btn = discord.ui.Button(
            label="Retour à la liste", emoji="📋", style=discord.ButtonStyle.primary, row=0
        )
        back_btn.callback = self.on_back
        next_btn = discord.ui.Button(
            label="Plat suivant",
            emoji="▶️",
            style=discord.ButtonStyle.secondary,
            disabled=self.detail_index >= len(self.menu_items) - 1,
            row=0,
        )
        next_btn.callback = self.on_next_item

        remove_btn = discord.ui.Button(
            label="Retirer", emoji="➖", style=discord.ButtonStyle.danger, disabled=qty == 0, row=1
        )
        remove_btn.callback = self.on_remove
        qty_btn = discord.ui.Button(
            label=f"{qty} au panier", style=discord.ButtonStyle.secondary, disabled=True, row=1
        )
        add_btn = discord.ui.Button(
            label="Ajouter", emoji="➕", style=discord.ButtonStyle.success, row=1
        )
        add_btn.callback = self.on_add

        for b in (prev_btn, back_btn, next_btn, remove_btn, qty_btn, add_btn):
            self.add_item(b)

    # ---------- Callbacks ----------
    async def on_select(self, interaction: discord.Interaction):
        self.detail_index = int(interaction.data["values"][0])
        await self.refresh(interaction)

    async def on_pay(self, interaction: discord.Interaction):
        if not self.cart:
            await interaction.response.send_message("Ton panier est vide.", ephemeral=True)
            return
        await interaction.response.send_modal(CheckoutModal(self))

    async def on_clear(self, interaction: discord.Interaction):
        self.cart.clear()
        await self.refresh(interaction)

    async def on_back(self, interaction: discord.Interaction):
        self.page = self.detail_index // self.per_page
        self.detail_index = None
        await self.refresh(interaction)

    async def on_prev_item(self, interaction: discord.Interaction):
        self.detail_index = max(0, self.detail_index - 1)
        await self.refresh(interaction)

    async def on_next_item(self, interaction: discord.Interaction):
        self.detail_index = min(len(self.menu_items) - 1, self.detail_index + 1)
        await self.refresh(interaction)

    async def on_add(self, interaction: discord.Interaction):
        self.cart[self.detail_index] = min(self.cart.get(self.detail_index, 0) + 1, 99)
        await self.refresh(interaction)

    async def on_remove(self, interaction: discord.Interaction):
        qty = self.cart.get(self.detail_index, 0) - 1
        if qty <= 0:
            self.cart.pop(self.detail_index, None)
        else:
            self.cart[self.detail_index] = qty
        await self.refresh(interaction)
