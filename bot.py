import discord
from discord.ext import commands, tasks
import aiohttp
import os
from datetime import datetime

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ETSY_API_KEY = os.getenv('ETSY_API_KEY')
ETSY_SHOP_ID = os.getenv('ETSY_SHOP_ID')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

last_checked_order_id = None

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    check_orders.start()

@tasks.loop(minutes=5)
async def check_orders():
    global last_checked_order_id
    
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return
    
    headers = {
        'x-api-key': ETSY_API_KEY,
    }
    
    url = f'https://openapi.etsy.com/v3/application/shops/{ETSY_SHOP_ID}/receipts'
    params = {
        'limit': 10,
        'sort_on': 'created',
        'sort_order': 'desc'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    orders = data.get('results', [])
                    
                    if orders:
                        newest_order_id = orders[0]['receipt_id']
                        
                        if last_checked_order_id is None:
                            last_checked_order_id = newest_order_id
                            await channel.send("📦 Etsy order monitoring started!")
                            return
                        
                        new_orders = []
                        for order in orders:
                            if order['receipt_id'] == last_checked_order_id:
                                break
                            new_orders.append(order)
                        
                        for order in reversed(new_orders):
                            embed = discord.Embed(
                                title="🎉 New Etsy Order!",
                                color=discord.Color.green(),
                                timestamp=datetime.fromtimestamp(order['create_timestamp'])
                            )
                            embed.add_field(name="Order ID", value=order['receipt_id'], inline=True)
                            embed.add_field(name="Total", value=f"${order['grandtotal']['amount']}/{order['grandtotal']['divisor']}", inline=True)
                            embed.add_field(name="Buyer", value=order.get('name', 'N/A'), inline=True)
                            embed.add_field(name="Status", value=order.get('status', 'N/A'), inline=True)
                            
                            await channel.send(embed=embed)
                        
                        if new_orders:
                            last_checked_order_id = newest_order_id
                else:
                    print(f"Error fetching orders: {response.status}")
    except Exception as e:
        print(f"Error: {e}")

@check_orders.before_loop
async def before_check_orders():
    await bot.wait_until_ready()

@bot.command()
async def orders(ctx):
    await ctx.send("Checking for recent orders...")
    await check_orders()

bot.run(DISCORD_TOKEN)
