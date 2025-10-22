import requests
import time

TOKEN = input("Введи токен бота: ").strip()
URL = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

print("\n🔄 Очищаем старые апдейты...")
resp = requests.get(URL, params={"timeout": 5})
data = resp.json()

if data.get("ok") and data.get("result"):
    last_id = data["result"][-1]["update_id"] + 1
    requests.get(URL, params={"offset": last_id})
    print("✅ Очередь очищена.")
else:
    print("✅ Очередь пуста.")

print("\nТеперь напиши любое сообщение в чат/топик, где бот добавлен.")
print("Скрипт будет ждать новое сообщение...\n")

offset = None
while True:
    try:
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset
        r = requests.get(URL, params=params, timeout=35)
        data = r.json()

        if not data.get("ok"):
            print("Ошибка:", data)
            time.sleep(2)
            continue

        for upd in data["result"]:
            offset = upd["update_id"] + 1
            msg = upd.get("message") or upd.get("channel_post")
            if not msg:
                continue

            chat_id = msg["chat"]["id"]
            thread_id = msg.get("message_thread_id")

            print(f"\n✅ chat_id: {chat_id}")
            print(f"🧵 thread_id: {thread_id}")
            exit()

    except KeyboardInterrupt:
        print("\nВыход.")
        break
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(3)
