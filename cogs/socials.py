import discord
from discord.ext import commands
from re import findall


class Socials(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.translations: dict[str, str] = \
            {
            "instagram.com": "kkinstagram.com",
            "x.com": "fixupx.com",
            "tiktok.com": "tnktok.com",
        }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        matches: list[str] = findall(
            r'(https?://[^\s]+)', message.content.lower())

        if len(matches) > 0:
            # Suppress embeds from original message
            await message.edit(suppress=True)
            for url in matches:
                for key in list(self.translations.keys()):
                    if key in url:
                        # Replace url with better embed
                        newMessage = url.replace(
                            key, self.translations[key])
                        # Remove query parameters
                        queryIndex = newMessage.find("?")
                        if queryIndex != -1:
                            newMessage = newMessage[:queryIndex]
                        # Send message
                        await message.reply(
                            f"{newMessage}",
                            mention_author=False
                        )
                        break


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Socials(bot))
