import discord
from discord.ext import commands
import re


class Socials(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.translations = [
            (re.compile(
                r"https://(?:www\.)?instagram\.com/reels/"),
                r"https://www.kkinstagram.com/reels/"),
            (re.compile(
                r"https://(?:www\.)?instagram\.com/p/"),
                r"https://www.kkinstagram.com/p/"),
            (re.compile(
                r"https://(?:www\.)?(?:x|twitter)\.com/([^/]+)/status/(\d+)"), 
                r"https://fixupx.com/\1/status/\2"),
            (re.compile(
                r"https://(?:[a-zA-Z0-9-]+\.)?tiktok\.com/"), 
                r"https://tnktok.com/"),
        ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        matches: list[str] = re.findall(
            r'(https?://[^\s]+)', message.content)
        supressed = False
        if len(matches) > 0:

            for url in matches:
                for pattern, replacement in self.translations:
                    if pattern.search(url):
                        if not supressed:
                            # Suppress embeds from original message     
                            await message.edit(suppress=True)
                            supressed = True
                        # Remove query parameters
                        query_index = url.find("?")
                        if query_index != -1:
                            url = url[:query_index]
                        # Replace url with better embed
                        new_message = pattern.sub(replacement, url)
                        # Send message
                        await message.reply(
                            f"{new_message}",
                            mention_author=False
                        )
                        break


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Socials(bot))
