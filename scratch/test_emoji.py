import asyncio
import os
from telegram import Bot

async def test_emoji():
    token = "8813750611:AAET-pru66SIHH9oYzRGPMTHvhdfCbUCei0"
    bot = Bot(token)
    chat_id = 7097905601  # user ID from the JSON
    try:
        msg = await bot.send_message(
            chat_id=chat_id,
            text='Testing emoji test_script: <tg-emoji emoji-id="5877332341331857066">📁</tg-emoji>',
            parse_mode="HTML"
        )
        print("Message sent successfully")
        print("Entities:", msg.entities)
    except Exception as e:
        print("Error:", e)

asyncio.run(test_emoji())
