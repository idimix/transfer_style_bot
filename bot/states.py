from aiogram.dispatcher.filters.state import StatesGroup, State


class States(StatesGroup):
    STATE_AWAIT_ORIGINAL_IMAGE = State()
    STATE_AWAIT_STYLE_IMAGE = State()
    STATE_AWAIT_STYLE_METHOD = State()
