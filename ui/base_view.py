from __future__ import annotations

import math

import discord

from utils.logger import print_error


class BaseView(discord.ui.View):
    """Vue réservée à son auteur, avec rafraîchissement et gestion du timeout."""

    unauthorized_message = "Seul l'auteur de la commande peut utiliser ces boutons."

    def __init__(self, author_id: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.message: discord.Message | None = None
        self.origin: discord.Interaction | None = None

    # ---------- À surcharger ----------
    def rebuild(self):
        raise NotImplementedError

    def build_embed(self) -> discord.Embed | None:
        return None

    # ---------- Rafraîchissement ----------
    async def refresh(self, interaction: discord.Interaction):
        self.rebuild()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def _edit_main(self, **kwargs):
        """Édite le message principal (éphémère ou non)."""
        if self.origin:
            await self.origin.edit_original_response(**kwargs)
        elif self.message:
            await self.message.edit(**kwargs)

    async def refresh_message(self):
        self.rebuild()
        try:
            await self._edit_main(embed=self.build_embed(), view=self)
        except discord.HTTPException as e:
            print_error("BaseView", f"Erreur refresh_message : {e!r}")

    # ---------- Vérifications / timeout ----------
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(self.unauthorized_message, ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self._edit_main(view=self)
        except discord.HTTPException:
            pass


class PaginatedView(BaseView):
    """BaseView avec pagination. Les sous-classes définissent per_page et total_items()."""

    per_page = 10

    def __init__(self, author_id: int, timeout: float = 300):
        super().__init__(author_id, timeout)
        self.page = 0

    def total_items(self) -> int:
        raise NotImplementedError

    @property
    def page_count(self) -> int:
        return max(1, math.ceil(self.total_items() / self.per_page))

    def clamp_page(self):
        self.page = max(0, min(self.page, self.page_count - 1))

    def page_slice(self, items: list) -> tuple[int, list]:
        """Retourne (index de départ, éléments de la page courante)."""
        start = self.page * self.per_page
        return start, items[start : start + self.per_page]

    def add_pagination_buttons(self, row: int = 1):
        prev_btn = discord.ui.Button(
            emoji="◀️", style=discord.ButtonStyle.primary, disabled=self.page == 0, row=row
        )
        prev_btn.callback = self.on_prev_page
        indicator = discord.ui.Button(
            label=f"{self.page + 1}/{self.page_count}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=row,
        )
        next_btn = discord.ui.Button(
            emoji="▶️",
            style=discord.ButtonStyle.primary,
            disabled=self.page >= self.page_count - 1,
            row=row,
        )
        next_btn.callback = self.on_next_page
        for b in (prev_btn, indicator, next_btn):
            self.add_item(b)

    async def on_prev_page(self, interaction: discord.Interaction):
        self.page = max(0, self.page - 1)
        await self.refresh(interaction)

    async def on_next_page(self, interaction: discord.Interaction):
        self.page = min(self.page_count - 1, self.page + 1)
        await self.refresh(interaction)
