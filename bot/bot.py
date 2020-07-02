from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import time
import threading
import queue
import requests
from collections import defaultdict
import os
import shutil

from states import States
from config import TOKEN
from model_transfer_style import transfer_style

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

# create dict for control 1 user - 1 calculating
calculations = defaultdict(bool)

# create a queue for calculating style transfer
queue_transfer_style = queue.Queue()


def send_photo(chat_id, photo):
    url = "https://api.telegram.org/bot{token}/sendPhoto".format(token=TOKEN)
    files = {'photo': photo}
    data = {'chat_id': chat_id}
    r = requests.post(url, files=files, data=data)
    print(r.status_code)


def transfer_style_send_photo(file_content, file_style, file_output, num_steps, chat_id):
    # print('Start')
    # time.sleep(10)
    # print('Stop')
    # model start
    transfer_style(file_content, file_style, file_output, num_steps=num_steps)

    with open(file_output, 'rb') as photo:
        send_photo(chat_id, photo)

    shutil.rmtree(os.path.join(os.getcwd(), 'chat_id_%s' % chat_id))
    calculations[chat_id] = False


class MyThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        process_queue()


def process_queue():
    while True:
        try:
            file_content, file_style, file_output, num_steps, chat_id = queue_transfer_style.get(block=False)
        except queue.Empty:
            pass
        else:
            transfer_style_send_photo(file_content, file_style, file_output, num_steps, chat_id)

        time.sleep(1)


thread1 = MyThread()
thread1.start()


@dp.message_handler(commands=['start', 'help'], state='*')
async def process_help_command(msg: types.Message):
    text = ('Hi! I can transfer style from any image to your image.\n\n'
            'You can control me by sending these commands:\n'
            '/style_transfer - style transfer\n')
    await bot.send_message(msg.from_user.id, text)


@dp.message_handler(commands=["style_transfer"], state='*')
async def style_transfer_command(msg: types.Message):
    chat_id = msg.from_user.id
    if calculations[chat_id]:
        await bot.send_message(chat_id, "Wait for the end")
    else:
        await bot.send_message(chat_id, "Send one jpg image to be processed")
        await States.STATE_AWAIT_ORIGINAL_IMAGE.set()
        folder_name = 'chat_id_%s' % chat_id
        if os.path.exists(folder_name):
            shutil.rmtree(os.path.join(os.getcwd(), folder_name))
        os.mkdir(folder_name)


@dp.message_handler(content_types=['photo'], state=States.STATE_AWAIT_ORIGINAL_IMAGE)
async def handle_get_original_photo(msg: types.Message):
    await States.STATE_AWAIT_STYLE_IMAGE.set()
    folder_name = 'chat_id_%s' % msg.from_user.id
    await msg.photo[-1].download(os.path.join(os.getcwd(), folder_name, 'original.jpg'))
    await bot.send_message(msg.from_user.id, "Send one jpg image that contains the style")


@dp.message_handler(content_types=['photo'], state=States.STATE_AWAIT_STYLE_IMAGE)
async def handle_get_transfer_strength(msg: types.Message):
    await States.STATE_AWAIT_TRANSFER_STRENGTH.set()
    folder_name = 'chat_id_%s' % msg.from_user.id
    await msg.photo[-1].download(os.path.join(os.getcwd(), folder_name, 'style.jpg'))
    await bot.send_message(msg.from_user.id, "Set the style transfer strength as a integer from 1 to 5")


@dp.message_handler(content_types=['text'], state=States.STATE_AWAIT_TRANSFER_STRENGTH)
async def handle_get_style_photo(msg: types.Message):
    if not msg.text in msg.text.strip() in list(map(str, range(1, 6))):
        await bot.send_message(msg.from_user.id, "Input integer from 1 to 5, try again")
        return

    transfer_strength = int(msg.text)
    num_steps = 100 * transfer_strength

    chat_id = msg.from_user.id
    folder_name = 'chat_id_%s' % chat_id

    await bot.send_message(chat_id, "Style transfer in progress...")
    file_content = os.path.join(os.getcwd(), folder_name, 'original.jpg')
    file_style = os.path.join(os.getcwd(), folder_name, 'style.jpg')
    file_output = os.path.join(os.getcwd(), folder_name, 'result.jpg')

    # adding a style transfer job to the queue
    queue_transfer_style.put((file_content, file_style, file_output, num_steps, chat_id))
    calculations[chat_id] = True


if __name__ == '__main__':
    executor.start_polling(dp)
