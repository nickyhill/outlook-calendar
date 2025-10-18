import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

from outlook_parser import OutlookParser



load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

parser = OutlookParser()


bot = commands.Bot(command_prefix='$', intents=intents)


@bot.event
async def on_ready():
    print(f'We are ready to go, {bot.user.name}')

@bot.event
async def on_member_join(member):

    general_channel = discord.utils.get(member.guild.text_channels, name="calendar")
    general_channel.send(f"Welcome to the server, {member.name}! 🎉")
    if general_channel:
        await general_channel.send(
            f"Everyone, please welcome {member.mention}! 🙌\n"
            "You can use the following commands to see ACPHS calendar events:\n"
            "`$cal today` - Events for today\n"
            "`$cal tomorrow` - Events for tomorrow\n"
            "`$cal <day>` - Events on a specific day of this month (e.g., `$cal 19`)\n"
            "`$cal <*> all` - All events on that particular day (e.g., `$cal today all`, `$cal 19 all`)"
        )


@bot.command()
async def cal(ctx, *, arg="today"):
    """
    Fetch ACPHS calendar events.
    Usage examples:
    $cal today       -> events today
    $cal tomorrow    -> events tomorrow
    $cal 20          -> events on the 20th of current month
    """
    global parser
    try:
        parser.set_command(str(arg))
        results = parser.run()
        message = "\n".join(results)
        await ctx.send(message)
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}\nRestarting parser...")
        try:
            parser.driver.quit()  # close broken driver
        except Exception:
            pass
        parser = OutlookParser(str(arg))  # reinit



bot.run(token, log_handler=handler, log_level=logging.DEBUG)
