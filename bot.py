import asyncio
import json
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()


def load_config():
    print("[LOG] Загружаем config.json...")
    with open("config.json", "r") as f:
        data = json.load(f)
    print("[LOG] Конфиг успешно загружен:", data)
    return data


def save_config(data):
    print("[LOG] Сохраняем config.json:", data)
    with open("config.json", "w") as f:
        json.dump(data, f, indent=2)
    print("[LOG] Конфиг сохранён.")


def get_schedule(group):
    print(f"[LOG] Получаем расписание для группы {group}...")
    try:
        response = requests.get(
            f"https://iis.bsuir.by/api/v1/schedule?studentGroup={group}"
        )
        response.raise_for_status()
        print("[LOG] Расписание успешно получено.")
        return response.json()
    except Exception as e:
        print("[ERROR] Ошибка получения расписания:", e)
        return {}


def get_current_week_number(start_date_str):
    if not start_date_str:
        print("[LOG] Нет даты начала семестра, возвращаем 1 неделю.")
        return 1

    start_date = datetime.strptime(start_date_str, "%d.%m.%Y")
    current_date = datetime.now()
    days_diff = (current_date - start_date).days
    week_number = ((days_diff // 7) + 1) % 4
    if (week_number == 0):
        week_number = 4
    print(f"[LOG] Текущая неделя: {week_number}")
    return max(1, week_number)


def get_tomorrow_lessons(group):
    print(f"[LOG] Получаем пары на завтра для группы {group}...")
    data = get_schedule(group)
    if not data:
        print("[LOG] Нет данных расписания.")
        return None

    tomorrow = datetime.now() + timedelta(days=1)
    days_map = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }
    tomorrow_day_name = days_map[tomorrow.weekday()]
    print(f"[LOG] Завтрашний день: {tomorrow_day_name}")

    schedules = data.get("schedules", {})
    tomorrow_schedule = schedules.get(tomorrow_day_name, [])
    if not tomorrow_schedule:
        print("[LOG] На завтра пар нет.")
        return None

    current_week = get_current_week_number(data.get("startDate"))
    lessons_options = []

    for lesson in tomorrow_schedule:
        if current_week not in lesson.get("weekNumber", []):
            continue
        subject = lesson.get("subject", "")
        type = lesson.get("lessonTypeAbbrev", "")
        subgroup = lesson.get("numSubgroup", 0)
        subgroup_info = f" (подгр. {subgroup})" if subgroup > 0 else ""
        option_text = f"не будет на {type} {subject} {subgroup_info}"
        lessons_options.append(option_text)

    print(f"[LOG] Найдено пар на завтра: {len(lessons_options)}")
    return lessons_options if lessons_options else None


async def send_daily_poll(chat_id: int, group: str):
    print(f"[LOG] Отправляем опрос в чат {chat_id} для группы {group}...")
    lessons = get_tomorrow_lessons(group)
    if not lessons:
        print("[LOG] Завтра пар нет — опрос не отправлен.")
        return

    question = f"{(datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')}"
    print(f"[LOG] Вопрос опроса: {question}")
    print(f"[LOG] Варианты: {lessons}")

    await bot.send_poll(
        chat_id=chat_id,
        question=question,
        options=lessons,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    print("[LOG] Первый опрос отправлен.")

    await bot.send_poll(
        chat_id=chat_id,
        question="причина",
        options=["уваж", "неуваж", "буду"],
        is_anonymous=False,
    )
    print("[LOG] Второй опрос отправлен.")


@dp.message(Command("start"))
async def start(message: types.Message):
    print(f"[LOG] Команда /start от {message.from_user.id}")
    config = load_config()
    config["chat_id"] = message.chat.id
    save_config(config)
    await message.answer(
        f"👋 Привет! Я бот расписания БГУИР\n\n"
        f"По умолчанию:\n"
        f"🧑‍🎓 Группа: {config['group']}\n"
        f"⏰ Время рассылки: {config['time']}\n\n"
        f"Команды:\n"
        f"/setgroup <номер> — сменить группу\n"
        f"/settime <часы:минуты> — сменить время рассылки"
    )
    print(f"[LOG] Chat ID {message.chat.id} сохранён.")


@dp.message(Command("setgroup"))
async def set_group(message: types.Message):
    print(f"[LOG] Команда /setgroup от {message.from_user.id}")
    args = message.text.split()
    if len(args) != 2:
        return await message.reply("⚠️ Используй формат: /setgroup 472302")

    group = args[1]
    config = load_config()
    config["group"] = group
    save_config(config)

    await message.reply(f"✅ Группа изменена на {group}")
    print(f"[LOG] Группа изменена на {group}")


@dp.message(Command("settime"))
async def set_time(message: types.Message):
    print(f"[LOG] Команда /settime от {message.from_user.id}")
    args = message.text.split()
    if len(args) != 2:
        return await message.reply("⚠️ Используй формат: /settime 22:00")

    new_time = args[1]
    print(f"[LOG] Устанавливаем новое время: {new_time}")
    config = load_config()
    config["time"] = new_time
    save_config(config)

    scheduler.remove_all_jobs()
    print("[LOG] Старые задачи планировщика удалены.")

    h, m = map(int, new_time.split(":"))
    chat_id = config.get("chat_id")
    group = config.get("group")

    if not chat_id:
        print("[WARN] Chat ID не найден. Пользователь должен выполнить /start.")
        return await message.reply("⚠️ Сначала напиши /start, чтобы я запомнил chat_id!")

    scheduler.add_job(send_daily_poll, "cron", hour=h, minute=m, args=[chat_id, group])
    print(f"[LOG] Новая задача добавлена на {h:02d}:{m:02d}")

    await message.reply(f"✅ Время рассылки изменено на {new_time}")


async def main():
    print("[LOG] Запуск бота...")
    config = load_config()
    h, m = map(int, config["time"].split(":"))
    chat_id = config.get("chat_id")
    group = config.get("group")

    if chat_id:
        print(f"[LOG] Планируем рассылку для чата {chat_id} ({group}) в {h:02d}:{m:02d}")
        scheduler.add_job(send_daily_poll, "cron", hour=h, minute=m, args=[chat_id, group])
    else:
        print("[WARN] Chat ID не найден. Напиши /start в боте, чтобы я его запомнил.")

    scheduler.start()
    print("[LOG] Планировщик запущен. Ожидание событий...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    print("[LOG] Старт программы main()")
    asyncio.run(main())
