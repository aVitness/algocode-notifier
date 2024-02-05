from io import BytesIO

import matplotlib.pyplot as plt
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

router = Router()


@router.message(Command("tex"))
async def latex(message: types.Message):
    fig = plt.figure()
    text = fig.text(0, 0, "$" + message.text[5:].replace('\n', "$\n$") + "$")
    dpi = 300
    fig.savefig(BytesIO(), dpi=dpi, format="png")
    bbox = text.get_window_extent()
    width, height = bbox.size / float(dpi) + 0.02
    fig.set_size_inches((width, height))
    dy = (bbox.ymin / float(dpi)) / height
    text.set_position((0, -dy))
    bytes = BytesIO()
    fig.savefig(bytes, dpi=dpi, format="png")
    bytes.seek(0)
    await message.answer_photo(BufferedInputFile(bytes.getvalue(), filename="tex.png"))
