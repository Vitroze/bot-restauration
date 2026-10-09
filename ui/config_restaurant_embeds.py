from __future__ import annotations

import discord

from utils.manage_restaurant import get_all_restaurants


class ConfigRestaurantEmbedsMixin:
    """Construction des embeds de la vue de configuration des restaurants."""

    # ---------- Embeds ----------
    def build_embed(self) -> discord.Embed:
        if self.mode == "list":
            return self.build_list_embed()
        return self.build_detail_embed()

    def build_list_embed(self) -> discord.Embed:
        restaurants = get_all_restaurants()
        names = self.names()
        start, chunk = self.page_slice(names)

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
            text=f"Page {self.page + 1}/{self.page_count} • {len(names)} "
            "restaurant(s) • Choisis-en un"
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
        embed.add_field(
            name="Plats au menu", value=str(len(restaurant.get("menu", []))), inline=True
        )
        embed.add_field(
            name="Réservations", value=str(len(restaurant.get("reservations", []))), inline=False
        )
        embed.add_field(
            name="Catégorie",
            value=(
                f"{self.origin.guild.get_channel(restaurant['category_id']).mention}"
                if restaurant.get("category_id")
                else "Aucune"
            ),
            inline=True,
        )

        count_permissions = len(restaurant.get("permissions", {}))
        if count_permissions > 0:
            roles_col, perms_col = [], []

            for role_id, perms in restaurant["permissions"].items():
                role = self.origin.guild.get_role(int(role_id)) if self.origin else None
                roles_col.append(role.mention if role else f"`{role_id}`")
                perms_col.append(", ".join(f"`{p}`" for p in perms) or "Aucune")

            embed.add_field(name="Rôle", value="\n".join(roles_col) or "Aucun", inline=True)
            embed.add_field(name="Permissions", value="\n".join(perms_col) or "Aucune", inline=True)
        else:
            embed.add_field(name="Rôles configurés", value="Aucun", inline=True)

        if self.mode == "confirm":
            embed.add_field(
                name="⚠️ Suppression",
                value="Cette action est **définitive**. Confirme pour supprimer ce restaurant.",
                inline=False,
            )
        return embed
