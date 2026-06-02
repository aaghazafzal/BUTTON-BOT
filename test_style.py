import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

async def test():
    bot = Bot(token="8813750611:AAET-pru66SIHH9oYzRGPMTHvhdfCbUCei0")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Blue", url="https://t.me", api_kwargs={"style": "primary"}),
        InlineKeyboardButton("Red", url="https://t.me", api_kwargs={"style": "danger"})
    ]])
    print("Testing if API accepts style parameter...")
    try:
        await bot.send_message(chat_id=123456789, text="Test", reply_markup=kb)
    except BadRequest as e:
        print("API Response:", e)

if __name__ == "__main__":
    asyncio.run(test())
