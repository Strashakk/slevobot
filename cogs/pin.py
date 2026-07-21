from discord.ext import commands
import discord

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Pin(bot))

class Pin(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.PIN_MIN = 5
        self.EMOJI = "📌"

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if str(payload.emoji) != self.EMOJI:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            channel = await self.bot.fetch_channel(payload.channel_id)

        try:
            message = await channel.fetch_message(payload.message_id)
            pin = list(filter(lambda x: str(x.emoji) == self.EMOJI,message.reactions))
            if len(pin) == 0:
                return
            members = [user async for user in pin[0].users()]
            pin_count = pin[0].count
            if pin_count >= self.PIN_MIN:
                if message.pinned:
                    return
                try:
                    await message.pin(reason="Pripnuté reakciami")
                except Exception as e:
                    msg = ""
                    if type(e).__name__ == "Forbidden":
                        msg = "Nedostatočné oprávnenia"
                    elif type(e).__name__ == "NotFound":
                        msg = "Správa alebo kanál nenájdený"
                    elif type(e).__name__ == "HTTPException":
                        msg = "Viac ako 250 pripnutých správ"

                    await channel.send(content=f"Nepodarilo sa pripnúť správu {message.jump_url}\nChyba: {msg}")
                    return

                for member in members:
                    try:
                        await message.remove_reaction(emoji=self.EMOJI,member=member)
                    except Exception as e:
                        print(e)


        except discord.NotFound:
            print("Message was deleted before it could be fetched.")
        except discord.Forbidden:
            print("Bot lacks permission to read message history in this channel.")
