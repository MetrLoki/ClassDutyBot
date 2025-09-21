import asyncio
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# -------------------------------
# Завантажуємо змінні з .env
# -------------------------------
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
TEACHER_ID = int(os.getenv("TEACHER_ID"))
GROUP_ID = int(os.getenv("GROUP_ID"))

# -------------------------------
# Логування
# -------------------------------
logging.basicConfig(level=logging.INFO)

# -------------------------------
# Ініціалізація бота
# -------------------------------
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# -------------------------------
# Список учнів
# -------------------------------
students = [
    "Вільчинська Анастасія",
    "Волков Богдан",
    "Голосна Катерина",
    "Каролець Наталія",
    "Колошва Андрій",
    "Корлотяну Антон",
    "Корнійчук Даніїл",
    "Лісняк Максим",
    "Мартовицька Поліна",
    "Мелешко Софія",
    "Натальчук Максим",
    "Новікова Аліна",
    "Рачковська Марина",
    "Савченко Анастасія",
    "Фоменко Світлана",
    "Хіміченко Нікіта",
    "Шавранська Яна",
    "Ящук Анна",
]

attendance = {}   # {username/full_name: {"status": "✅/❌", "reason": "ПП/ХВ/БП"} }
queue = students.copy()  # черга для чергування
current_duty = None

# -------------------------------
# Клавіатури
# -------------------------------
def presence_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="✅ Присутній")
    kb.button(text="❌ Відсутній")
    return kb.as_markup(resize_keyboard=True)

def absence_reason_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="ПП")
    kb.button(text="ХВ")
    kb.button(text="БП")
    return kb.as_markup(resize_keyboard=True)

def duty_done_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.button(text="✅ Виконав")
    kb.button(text="❌ Не виконав")
    return kb.as_markup(resize_keyboard=True)

# -------------------------------
# Логіка бота
# -------------------------------
async def ask_attendance():
    await bot.send_message(GROUP_ID, "Доброго ранку! Відмітьте свою присутність 👇", reply_markup=presence_keyboard())

async def finalize_attendance():
    global current_duty
    present = [name for name, data in attendance.items() if data["status"] == "✅"]

    if not present:
        await bot.send_message(TEACHER_ID, "❌ Ніхто не відмітився присутнім!")
        return

    # вибираємо першого з черги, хто присутній
    for name in queue:
        if name in present:
            current_duty = name
            queue.remove(name)
            queue.append(name)
            break

    # формуємо звіт
    text = f"📋 Присутність на {datetime.now().date()}:\n\n"
    for name in students:
        if name in attendance:
            st = attendance[name]["status"]
            reason = attendance[name].get("reason", "")
            duty = "🟢 (черговий)" if name == current_duty else ""
            text += f"{st} {name} {reason} {duty}\n"
        else:
            text += f"❌ {name} (не відповів)\n"

    # надсилаємо вчителю та групі
    await bot.send_message(TEACHER_ID, text)
    await bot.send_message(GROUP_ID, text)

async def ask_duty_done():
    if current_duty:
        await bot.send_message(GROUP_ID, f"{current_duty}, чи виконав ти обов’язки сьогодні?", reply_markup=duty_done_keyboard())

# -------------------------------
# Хендлери
# -------------------------------
@dp.message(F.text == "✅ Присутній")
async def mark_present(message: types.Message):
    name = message.from_user.full_name
    attendance[name] = {"status": "✅"}
    await message.answer("Відмічено: присутній", reply_markup=types.ReplyKeyboardRemove())

@dp.message(F.text == "❌ Відсутній")
async def ask_reason(message: types.Message):
    await message.answer("Вкажи причину відсутності:", reply_markup=absence_reason_keyboard())

@dp.message(F.text.in_(["ПП", "ХВ", "БП"]))
async def mark_absent(message: types.Message):
    name = message.from_user.full_name
    attendance[name] = {"status": "❌", "reason": f"({message.text})"}
    await message.answer("Відмічено: відсутній", reply_markup=types.ReplyKeyboardRemove())

@dp.message(F.text.in_(["✅ Виконав", "❌ Не виконав"]))
async def duty_status(message: types.Message):
    status = "Виконав" if "✅" in message.text else "Не виконав"
    await bot.send_message(TEACHER_ID, f"📌 Черговий {current_duty} — {status}")
    await message.answer("Дякую, твоя відповідь записана.", reply_markup=types.ReplyKeyboardRemove())

# -------------------------------
# Планувальник завдань
# -------------------------------
async def on_startup():
    scheduler.add_job(ask_attendance, "cron", hour=8, minute=0)
    scheduler.add_job(finalize_attendance, "cron", hour=8, minute=30)
    scheduler.add_job(ask_duty_done, "cron", hour=15, minute=0)
    scheduler.start()

# -------------------------------
# Запуск бота
# -------------------------------
async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
