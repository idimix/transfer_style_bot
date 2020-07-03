from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
import time
import threading
import queue
import requests
from collections import defaultdict
import os
import shutil

from states import States
from config import TOKEN
from gatys_net import transfer_style as transfer_style_slow
from msg_net import transfer_style as transfer_style_fast

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
    # print(r.status_code)


def send_message(chat_id, text):
    url = "https://api.telegram.org/bot{token}/sendMessage".format(token=TOKEN)
    data = {'chat_id': chat_id, 'text': text}
    r = requests.post(url, data=data)
    # print(r.status_code)


def transfer_style_send_photo(model_name, file_content, file_style, file_output, chat_id):
    # print('Start')
    # time.sleep(10)
    # print('Stop')
    # model start
    if model_name == '/gatys':
        transfer_style_slow(file_content, file_style, file_output)
    elif model_name == '/msg':
        transfer_style_fast(file_content, file_style, file_output)
    else:
        print('Error! Model name wrong')

    if os.path.exists(file_content):
        with open(file_content, 'rb') as photo:
            send_photo(chat_id, photo)

    send_message(chat_id, 'Try again? Send the command /style_transfer')

    folder_name = os.path.join(os.getcwd(), 'chat_id_%s' % chat_id)
    if os.path.exists(folder_name):
        shutil.rmtree(folder_name)
    calculations[chat_id] = False


class MyThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        process_queue()


def process_queue():
    while True:
        try:
            model_name, file_content, file_style, file_output, chat_id = queue_transfer_style.get(block=False)
        except queue.Empty:
            pass
        else:
            transfer_style_send_photo(model_name, file_content, file_style, file_output, chat_id)

        time.sleep(1)


thread1 = MyThread()
thread1.start()


@dp.message_handler(commands=['start'], state='*')
async def process_help_command(msg: types.Message):
    text = (
        'Hi! I can transfer style from any image to your image.\n\n'
        'You can control me by sending these commands:\n'
        '/style_transfer - style transfer\n'
        '/help - detailed instructions'
    )
    await bot.send_message(msg.from_user.id, text)


@dp.message_handler(commands=['help'], state='*')
async def process_help_command(msg: types.Message):
    text = (
        "To start the transfer of the style, you need:\n"
        "1. to send the command /style_transfer\n"
        "2. to send one image that needs to be processed\n"
        "3. to send one image that contains the style\n"
        '4. to choose a style transfer algorithm: '
        'A Neural Algorithm of Artistic Style https://arxiv.org/abs/1508.06576 or '
        'Multi-style Generative Network for Real-time Transfer https://arxiv.org/abs/1703.06953\n\n'
        "Let's start!"
    )
    await bot.send_message(msg.from_user.id, text)


@dp.message_handler(commands=["style_transfer"], state='*')
async def style_transfer_command(msg: types.Message):
    chat_id = msg.from_user.id
    if calculations[chat_id]:
        await bot.send_message(chat_id, "Wait for the end")
    else:
        await bot.send_message(chat_id, "Send one jpg image as photo to be processed")
        await States.STATE_AWAIT_ORIGINAL_IMAGE.set()
        folder_name = os.path.join(os.getcwd(), 'chat_id_%s' % chat_id)
        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.mkdir(folder_name)


@dp.message_handler(content_types=['photo'], state=States.STATE_AWAIT_ORIGINAL_IMAGE)
async def handle_get_original_photo(msg: types.Message):
    await States.STATE_AWAIT_STYLE_IMAGE.set()
    folder_name = 'chat_id_%s' % msg.from_user.id
    await msg.photo[-1].download(os.path.join(os.getcwd(), folder_name, 'original.jpg'))
    await bot.send_message(msg.from_user.id, "Send one jpg image as photo that contains the style")


@dp.message_handler(content_types=['photo'], state=States.STATE_AWAIT_STYLE_IMAGE)
async def handle_get_transfer_strength(msg: types.Message):
    await States.STATE_AWAIT_STYLE_METHOD.set()
    folder_name = 'chat_id_%s' % msg.from_user.id
    await msg.photo[-1].download(os.path.join(os.getcwd(), folder_name, 'style.jpg'))
    text = (
        'Set the style transfer method by sending one of two commands:\n'
        '/gatys - A Neural Algorithm of Artistic Style (slow)\n'
        '/msg - Multi-style Generative Network for Real-time Transfer (fast)'
    )
    await bot.send_message(msg.from_user.id, text)


@dp.message_handler(commands=['gatys', 'msg'], state=States.STATE_AWAIT_STYLE_METHOD)
async def handle_get_style_photo(msg: types.Message, state: FSMContext):
    chat_id = msg.from_user.id
    folder_name = 'chat_id_%s' % chat_id

    await bot.send_message(chat_id, "Style transfer in progress...")
    file_content = os.path.join(os.getcwd(), folder_name, 'original.jpg')
    file_style = os.path.join(os.getcwd(), folder_name, 'style.jpg')
    file_output = os.path.join(os.getcwd(), folder_name, 'result.jpg')

    # adding a style transfer job to the queue
    model_name = msg.get_command().lower()
    queue_transfer_style.put((model_name, file_content, file_style, file_output, chat_id))
    calculations[chat_id] = True

    await state.finish()


@dp.message_handler(state='*')
async def process_help_command(msg: types.Message):
    await bot.send_message(msg.from_user.id, 'Follow the instructions above. If you don’t know what to do send a command /help')

if __name__ == '__main__':
    executor.start_polling(dp)
