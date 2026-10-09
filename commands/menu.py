import asyncio
import math
import discord
from discord import app_commands
from discord.ext import commands

from models.restaurant import Restaurant
from utils.manage_restaurant import RestaurantTransformer

PER_PAGE = 5


def to_float(price) -> float:
    try:
        return float(price)
    except (TypeError, ValueError):
        return 0.0

def get_role_chef(restaurant: Restaurant, guild: discord.Guild) -> list[discord.Role]:
    """Rôles ayant la permission take_command pour ce restaurant."""
    roles = []
    for role_id, perms in restaurant.permissions.items():
        if "take_command" in perms:
            role = guild.get_role(int(role_id))
            if role:
                roles.append(role)
    return roles

def format_price(price) -> str:
    try:
        return f"{float(price):.2f} €".replace(".", ",")
    except (TypeError, ValueError):
        return f"{price} €"

import re
def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:30] or "client"


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
            await interaction.response.send_message("Commande impossible en message privé.", ephemeral=True)
            return
        if not view.cart:
            await interaction.response.send_message("Ton panier est vide.", ephemeral=True)
            return

        await interaction.response.defer()

        chef_roles = get_role_chef(view.restaurant, guild)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        for role in chef_roles:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        category = getattr(interaction.channel, "category", None)
        existing_channel = discord.utils.get(
            guild.text_channels,
            name=f"commande-{slugify(interaction.user.name)}",
            category=category
        )

        if existing_channel:
            await interaction.followup.send(
                f"❌ Tu as déjà une commande en cours : {existing_channel.mention}",
                ephemeral=True,
            )
            return

        try:
            channel = await guild.create_text_channel(
                name=f"commande-{slugify(interaction.user.name)}",
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
            await interaction.followup.send(f"❌ Impossible de créer le salon : {e}", ephemeral=True)
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

        chefs = " ".join(r.mention for r in chef_roles) or "*Aucun chef configuré pour ce restaurant*"
        order_view = OrderView(interaction.user.id, [r.id for r in chef_roles])
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
        await interaction.followup.send(f"✅ Commande envoyée ! Suis-la ici : {channel.mention}", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(f"Erreur modal paiement : {error!r}")
        if interaction.response.is_done():
            await interaction.followup.send("Une erreur est survenue.", ephemeral=True)
        else:
            await interaction.response.send_message("Une erreur est survenue.", ephemeral=True)


class MenuUI(discord.ui.View):
    def __init__(self, restaurant, menu_items: list[dict], author_id: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.restaurant = restaurant
        self.menu_items = menu_items
        self.author_id = author_id
        self.page = 0
        self.detail_index: int | None = None  # None = mode liste
        self.cart: dict[int, int] = {}        # index du plat -> quantité
        self.message: discord.Message | None = None
        self.rebuild()

    @property
    def page_count(self) -> int:
        return max(1, math.ceil(len(self.menu_items) / PER_PAGE))

    # ---------- Panier ----------
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
        start = self.page * PER_PAGE
        chunk = self.menu_items[start:start + PER_PAGE]
        lines = [f"**{start + i + 1}.** {item.get('name', 'Sans nom')}" for i, item in enumerate(chunk)]

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
            embed.add_field(name=f"🛒 Votre panier ({self.cart_count()})", value=cart_text, inline=False)
            embed.add_field(name="Total", value=f"**{format_price(self.cart_total())}**", inline=False)
        else:
            embed.add_field(name="🛒 Votre panier", value="*Vide*", inline=False)

        embed.set_footer(text=f"Page {self.page + 1}/{self.page_count} • Choisis un plat pour voir le détail")
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
        embed.add_field(name="Dans le panier", value=str(self.cart.get(self.detail_index, 0)), inline=True)
        if item.get("picture_url"):
            embed.set_image(url=item["picture_url"])
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
        start = self.page * PER_PAGE
        chunk = self.menu_items[start:start + PER_PAGE]

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

        prev_btn = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.primary,
                                     disabled=self.page == 0, row=1)
        prev_btn.callback = self.on_prev_page
        indicator = discord.ui.Button(label=f"{self.page + 1}/{self.page_count}",
                                      style=discord.ButtonStyle.secondary, disabled=True, row=1)
        next_btn = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.primary,
                                     disabled=self.page >= self.page_count - 1, row=1)
        next_btn.callback = self.on_next_page

        pay_btn = discord.ui.Button(label="Payer", emoji="💳", style=discord.ButtonStyle.success,
                                    disabled=not self.cart, row=2)
        pay_btn.callback = self.on_pay
        clear_btn = discord.ui.Button(label="Vider le panier", emoji="🗑️", style=discord.ButtonStyle.danger,
                                      disabled=not self.cart, row=2)
        clear_btn.callback = self.on_clear

        for b in (prev_btn, indicator, next_btn, pay_btn, clear_btn):
            self.add_item(b)

    def _add_detail_components(self):
        qty = self.cart.get(self.detail_index, 0)

        prev_btn = discord.ui.Button(emoji="◀️", label="Plat précédent", style=discord.ButtonStyle.secondary,
                                     disabled=self.detail_index == 0, row=0)
        prev_btn.callback = self.on_prev_item
        back_btn = discord.ui.Button(label="Retour à la liste", emoji="📋", style=discord.ButtonStyle.primary, row=0)
        back_btn.callback = self.on_back
        next_btn = discord.ui.Button(label="Plat suivant", emoji="▶️", style=discord.ButtonStyle.secondary,
                                     disabled=self.detail_index >= len(self.menu_items) - 1, row=0)
        next_btn.callback = self.on_next_item

        remove_btn = discord.ui.Button(label="Retirer", emoji="➖", style=discord.ButtonStyle.danger,
                                       disabled=qty == 0, row=1)
        remove_btn.callback = self.on_remove
        qty_btn = discord.ui.Button(label=f"{qty} au panier", style=discord.ButtonStyle.secondary,
                                    disabled=True, row=1)
        add_btn = discord.ui.Button(label="Ajouter", emoji="➕", style=discord.ButtonStyle.success, row=1)
        add_btn.callback = self.on_add

        for b in (prev_btn, back_btn, next_btn, remove_btn, qty_btn, add_btn):
            self.add_item(b)

    async def refresh(self, interaction: discord.Interaction):
        self.rebuild()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    # ---------- Callbacks : liste ----------
    async def on_select(self, interaction: discord.Interaction):
        self.detail_index = int(interaction.data["values"][0])
        await self.refresh(interaction)

    async def on_prev_page(self, interaction: discord.Interaction):
        self.page = max(0, self.page - 1)
        await self.refresh(interaction)

    async def on_next_page(self, interaction: discord.Interaction):
        self.page = min(self.page_count - 1, self.page + 1)
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
        self.page = self.detail_index // PER_PAGE
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

    # ---------- Sécurité / expiration ----------
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Seul l'auteur de la commande peut naviguer. Utilise `/menu` pour avoir le tien.",
                ephemeral=True,
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


class Menu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    RestaurantNameTransformer = app_commands.Transform[Restaurant, RestaurantTransformer]

    @app_commands.command(name="menu", description="Affiche le menu d'un restaurant.")
    @app_commands.describe(restaurant="Le nom du restaurant dont vous voulez voir le menu.")
    async def menu(self, interaction: discord.Interaction, restaurant: RestaurantNameTransformer):
        if not restaurant:
            await interaction.response.send_message("Le restaurant spécifié n'existe pas.", ephemeral=True)
            return

        if not restaurant.menu:
            await interaction.response.send_message(
                f"Le restaurant {restaurant.name} n'a pas de menu disponible.", ephemeral=True
            )
            return

        view = MenuUI(restaurant, restaurant.menu, interaction.user.id)
        await interaction.response.send_message(embed=view.build_embed(), view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Menu(bot))