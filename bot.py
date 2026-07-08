import asyncio
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    PreCheckoutQuery,
)

from database import get_balance, init_db, update_balance

BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER_TOKEN = ""

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎰 Играть (10 Stars)", callback_data="play_slots"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Купить Stars (Пополнить)",
                    callback_data="buy_stars",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Мой баланс", callback_data="check_balance"
                )
            ],
        ]
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await get_balance(message.from_user.id)
    await message.answer(
        "🎰 Добро пожаловать в Blackhol Stars Casino!\n\n"
        "Испробуйте удачу и выигрывайте звезды!",
        reply_markup=main_keyboard(),
    )


@dp.callback_query(F.data == "check_balance")
async def process_balance(callback: types.CallbackQuery):
    balance = await get_balance(callback.from_user.id)
    await callback.message.edit_text(
        f"💰 Ваш баланс: {balance} ⭐ Stars", reply_markup=main_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "buy_stars")
async def process_buy(callback: types.CallbackQuery):
    prices = [LabeledPrice(label="100 Telegram Stars", amount=100)]
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Пополнение баланса",
        description="Покупка 100 Stars для игры в Blackhol Stars",
        payload="deposit_100_stars",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="XTR",
        prices=prices,
        start_parameter="casino-deposit",
    )
    await callback.answer()


@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    amount = message.successful_payment.total_amount
    await update_balance(message.from_user.id, amount)
    await message.answer(
        f"✅ Оплата прошла успешно! Зачислено {amount} ⭐ Stars.",
        reply_markup=main_keyboard(),
    )


@dp.callback_query(F.data == "play_slots")
async def process_play(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bet = 10
    balance = await get_balance(user_id)

    if balance < bet:
        await callback.answer(
            "❌ Недостаточно Stars! Пополните баланс.", show_alert=True
        )
        return

    await update_balance(user_id, -bet)

    dice_msg = await bot.send_dice(
        chat_id=callback.message.chat.id, emoji="🎰"
    )
    value = dice_msg.dice.value

    await asyncio.sleep(2)

    if value == 64:
        win_amount = 250
        await update_balance(user_id, win_amount)
        result_text = f"🎉 ДЖЕКПОТ! Вы выиграли {win_amount} ⭐ Stars!"
    elif value in [1, 22, 43]:
        win_amount = 30
        await update_balance(user_id, win_amount)
        result_text = f"✨ Три в ряд! Вы выиграли {win_amount} ⭐ Stars!"
    else:
        result_text = "❌ Увы, не повезло. Попробуйте еще раз!"

    new_balance = await get_balance(user_id)
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=f"{result_text}\n\n💰 Текущий баланс: {new_balance} ⭐",
        reply_markup=main_keyboard(),
    )
    await callback.answer()


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
