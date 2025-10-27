import json
import requests
from datetime import datetime, timedelta


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


def get_schedule(group):
    try:
        r = requests.get(
            f"https://iis.bsuir.by/api/v1/schedule?studentGroup={group}", timeout=10
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Ошибка получения расписания:", e)
        return {}


def get_current_week_number(start_date_str):
    if not start_date_str:
        return 1
    start_date = datetime.strptime(start_date_str, "%d.%m.%Y")
    days_diff = (datetime.now() - start_date).days
    week_number = ((days_diff // 7) + 1) % 4
    if week_number == 0:
        week_number = 4
    return max(1, week_number)


def get_tomorrow_lessons(group):
    data = get_schedule(group)
    if not data:
        return None

    tomorrow = datetime.now() #+ timedelta(days=1)
    days_map = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }
    day_name = days_map[tomorrow.weekday()]
    schedules = data.get("schedules", {})
    day_sched = schedules.get(day_name, [])
    if not day_sched:
        return None

    current_week = get_current_week_number(data.get("startDate"))
    exclude_keywords = ["К.Ч.", "ИнФЧ", "ФизК", "Инф. час"]
    options = []

    for lesson in day_sched:
        if current_week not in lesson.get("weekNumber", []):
            continue

        subject = lesson.get("subject", "")
        note = lesson.get("note") or ""

        # Пропускаем ненужные пары азазахвхахаахах
        if any(k in subject for k in exclude_keywords):
            continue

        if "только" in note.lower():
            continue

        t = lesson.get("lessonTypeAbbrev", "")
        subgroup = lesson.get("numSubgroup", 0)
        sg = f" (подгр. {subgroup})" if subgroup > 0 else ""
        options.append(f"не буду на {t} {subject}{sg}")

    return options if options else None


def send_poll_via_api(
    bot_token,
    chat_id,
    question,
    options,
    message_thread_id=None,
    anonymous=False,
    multiple=False,
):
    url = f"https://api.telegram.org/bot{bot_token}/sendPoll"
    data = {
        "chat_id": chat_id,
        "question": question,
        "options": json.dumps(options),
        "is_anonymous": str(anonymous).lower(),
        "allows_multiple_answers": str(multiple).lower(),
        "message_thread_id": message_thread_id,
    }

    r = requests.post(url, data=data, timeout=10)
    try:
        r.raise_for_status()
    except Exception as e:
        print("Ошибка отправки опроса:", r.text, e)
    return r.json()


def main():
    cfg = load_config()
    bot_token = cfg["BOT_TOKEN"]
    chat_id = cfg["chat_id"]
    group = cfg["group"]
    thread_id = cfg["thread_id"]

    lessons = get_tomorrow_lessons(group)
    if not lessons:
        print("На завтра пар нет. Опрос не отправлен.")
        return

    question = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    print(len(lessons))
    lessons.append("буду везде")

    send_poll_via_api(
        bot_token,
        chat_id,
        question,
        lessons,
        message_thread_id=thread_id,
        anonymous=False,
        multiple=True,
    )

    # Второй опрос с причинами
    send_poll_via_api(
        bot_token,
        chat_id,
        "причина",
        ["уваж", "неуваж", "буду"],
        message_thread_id=thread_id,
        anonymous=False,
        multiple=False,
    )


if __name__ == "__main__":
    main()
