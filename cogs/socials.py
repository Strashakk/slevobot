import discord
from discord.ext import commands


class Socials(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Ignore bot messages, including this bot itself.
        if message.author.bot:
            return

        # Add your per-message processing here.
        # Example: detect and replace social media links.
        message_content = message.content.lower()
        if "instagram.com" in message_content:
            newMessage = message.content.replace("instagram.com", "kkinstagram.com")
            await message.channel.send(
                f"{newMessage}"
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Socials(bot))