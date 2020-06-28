from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from model import transfer_style

from config import TOKEN
import os
import shutil

from aiogram.dispatcher.filters.state import StatesGroup, State


class States(StatesGroup):
    STATE_AWAIT_ORIGINAL_IMAGE = State()
    STATE_AWAIT_STYLE_IMAGE = State()
    # STATE_GET_STYLE_IMAGE = State()


bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())


@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    await message.reply("Привет!\nЧтобы перенести стиль введи команду /style_transfer и следуй инстуркциям")


# @dp.message_handler()
# async def echo_message(msg: types.Message):
#     await bot.send_message(msg.from_user.id, msg.text)


@dp.message_handler(commands=["style_transfer"], state='*')
async def style_transfer_command(message: types.Message):
    await message.reply("Отправь одну картинку в формате jpg, которую нужно обработать")
    await States.STATE_AWAIT_ORIGINAL_IMAGE.set()
    folder_name = 'user_%s' % message.from_user.id
    if os.path.exists(folder_name):
        shutil.rmtree(os.path.join(os.getcwd(), folder_name))
    os.mkdir(folder_name)


@dp.message_handler(content_types=['photo'], state=States.STATE_AWAIT_ORIGINAL_IMAGE)
async def handle_get_original_photo(message: types.Message):
    await States.STATE_AWAIT_STYLE_IMAGE.set()
    folder_name = 'user_%s' % message.from_user.id
    await message.photo[-1].download(os.path.join(os.getcwd(), folder_name, 'original.jpg'))
    await message.reply("Теперь отправь одну картинку в формате jpg, которая содержит стиль")


@dp.message_handler(content_types=['photo'], state=States.STATE_AWAIT_STYLE_IMAGE)
async def handle_get_original_photo(message: types.Message):
    # await States.STATE_AWAIT_STYLE_IMAGE.set()
    folder_name = 'user_%s' % message.from_user.id
    await message.photo[-1].download(os.path.join(os.getcwd(), folder_name, 'style.jpg'))
    await message.reply("Идет процесс переноса стиля...")
    # запуск модели, в модель на вход передается путь к картинкам
    transfer_style(
        file_content=os.path.join(os.getcwd(), folder_name, 'original.jpg'),
        file_style=os.path.join(os.getcwd(), folder_name, 'style.jpg'),
        file_output=os.path.join(os.getcwd(), folder_name, 'result.jpg')
    )
    with open(os.path.join(os.getcwd(), folder_name, 'result.jpg'), 'rb') as photo:
        await message.reply_photo(photo, caption='Готово!')



if __name__ == '__main__':
    executor.start_polling(dp)
