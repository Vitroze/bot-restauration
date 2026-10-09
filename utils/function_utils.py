import discord

from models.restaurant import Restaurant


def to_float(price) -> float:
    try:
        return float(price)
    except (TypeError, ValueError):
        return 0.0


def format_price(price) -> str:
    try:
        return f"{float(price):.2f} €".replace(".", ",")
    except (TypeError, ValueError):
        return f"{price} €"


async def is_valid_emoji(self, emoji: str) -> bool:
    emoji = emoji.strip()

    if emoji.startswith("<") and emoji.endswith(">"):
        try:
            partial_emoji = discord.PartialEmoji.from_str(emoji)
        except Exception:
            return False
        return partial_emoji.id is not None and self.bot.get_emoji(partial_emoji.id) is not None

    if discord.utils.get(self.bot.emojis, name=emoji) is not None:
        return True

    if emoji.isdigit() and self.bot.get_emoji(int(emoji)) is not None:
        return True

    return bool(emoji) and not emoji.isascii()


def get_role_chef(restaurant: Restaurant, guild: discord.Guild) -> list[discord.Role]:
    """Rôles ayant la permission take_command pour ce restaurant."""
    roles = []
    for role_id, perms in restaurant.permissions.items():
        if "take_command" in perms:
            role = guild.get_role(int(role_id))
            if role:
                roles.append(role)
    return roles
