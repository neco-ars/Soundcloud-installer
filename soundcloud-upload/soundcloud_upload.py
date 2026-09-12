#!/usr/bin/env python3
"""
soundcloud_upload.py — простой инструмент для загрузки трека на SoundCloud
через автоматизацию браузера (Playwright), без официального API.

ПЕРВЫЙ ЗАПУСК (один раз, чтобы залогиниться):
    python soundcloud_upload.py --login

ОБЫЧНОЕ ИСПОЛЬЗОВАНИЕ:
    python soundcloud_upload.py "путь/к/треку.mp3" --title "Название трека"

Доп. флаги:
    --private            сделать трек приватным (по умолчанию — публичный)
    --tags "tag1 tag2"    теги через пробел
    --description "..."   описание трека
    --no-close            не закрывать браузер после загрузки (посмотреть результат)

Требования (установить один раз):
    pip install playwright
    playwright install chromium
"""

import argparse
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("Не найден playwright. Установи так:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)

if getattr(sys, "frozen", False):
    # Запущено как собранный .exe (PyInstaller) — берём папку рядом с exe
    SCRIPT_DIR = Path(sys.executable).resolve().parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent

PROFILE_DIR = SCRIPT_DIR / "sc_browser_profile"  # тут хранится твоя залогиненная сессия


def do_login():
    """Открывает браузер, чтобы ты вручную залогинился. Сессия сохранится в PROFILE_DIR."""
    PROFILE_DIR.mkdir(exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=False
        )
        page = context.new_page()
        page.goto("https://soundcloud.com/")
        print("\n>>> Залогинься в SoundCloud в открывшемся окне браузера.")
        print(">>> Если окно/форма выглядит пустой — обнови страницу (F5), не закрывай окно сам.")
        input(">>> Когда залогинишься — вернись сюда и нажми Enter... ")
        try:
            context.close()
        except Exception:
            print(">>> Окно браузера уже было закрыто вручную — если ты успел залогиниться, сессия могла не сохраниться.")
            print(">>> Если после этого запуск скрипта попросит логиниться снова — просто повтори --login и не закрывай окно сам.")
    print("Готово (или почти). Проверь ниже, не появилось ли предупреждение выше.")


def try_selectors(page, selectors, action, timeout=5000):
    """Пробует по очереди несколько селекторов, пока один не сработает."""
    for sel in selectors:
        try:
            locator = page.locator(sel).first
            locator.wait_for(state="visible", timeout=timeout)
            action(locator)
            return True
        except Exception:
            continue
    return False


def upload_track(file_path: str, title: str, private: bool, tags: str, description: str, keep_open: bool):
    file_path = str(Path(file_path).expanduser().resolve())
    if not Path(file_path).exists():
        print(f"Файл не найден: {file_path}")
        sys.exit(1)
    if not PROFILE_DIR.exists():
        print("Похоже, ты ещё не логинился. Сначала запусти:")
        print("  python soundcloud_upload.py --login")
        sys.exit(1)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=False
        )
        page = context.new_page()
        page.goto("https://soundcloud.com/upload")
        page.wait_for_load_state("networkidle")

        # 1. Загружаем сам файл через input[type=file]
        try:
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(file_path, timeout=15000)
        except Exception:
            print("\n>>> Не смог найти поле загрузки файла автоматически.")
            print(">>> Перетащи файл в окно браузера вручную, дождись обработки,")
            input(">>> затем нажми Enter здесь, чтобы продолжить... ")

        print("Файл отправлен, ждём обработки/редактора трека...")

        # 2. Ждём, пока откроется форма редактирования трека (появится поле title)
        title_selectors = [
            'input[name="title"]',
            'input[placeholder*="title" i]',
            'input[placeholder*="назван" i]',
            'textarea[name="title"]',
        ]

        found_title = try_selectors(
            page, title_selectors,
            lambda loc: (loc.click(), loc.fill(""), loc.type(title)),
            timeout=60000,
        )

        if not found_title:
            print("\n>>> Не нашёл автоматически поле 'Название трека'.")
            print(">>> Впиши название сам в открывшемся окне браузера.")
            input(">>> Нажми Enter здесь, когда закончишь с названием... ")

        # 3. Описание (необязательно)
        if description:
            desc_selectors = [
                'textarea[name="description"]',
                'textarea[placeholder*="description" i]',
            ]
            try_selectors(page, desc_selectors, lambda loc: (loc.click(), loc.fill(description)))

        # 4. Теги (необязательно)
        if tags:
            tag_selectors = [
                'input[name="tag_list"]',
                'input[placeholder*="tag" i]',
            ]
            try_selectors(page, tag_selectors, lambda loc: (loc.click(), loc.type(tags + " ")))

        # 5. Приватность
        if private:
            privacy_selectors = [
                'text=Private',
                '[data-testid="privacy-private"]',
                'label:has-text("Private")',
            ]
            ok = try_selectors(page, privacy_selectors, lambda loc: loc.click())
            if not ok:
                print("\n>>> Не смог автоматически поставить 'Private' — выбери вручную в окне браузера.")
                input(">>> Нажми Enter, когда выберешь приватность... ")

        # 6. Сохранение / публикация
        save_selectors = [
            'button:has-text("Save")',
            'button:has-text("Сохранить")',
            '[data-testid="save-button"]',
        ]
        saved = try_selectors(page, save_selectors, lambda loc: loc.click(), timeout=10000)

        if not saved:
            print("\n>>> Не нашёл кнопку 'Save' автоматически.")
            print(">>> Нажми её сам в окне браузера, когда всё будет готово.")
            input(">>> Нажми Enter здесь после сохранения... ")
        else:
            print("Нажал 'Save'. Ждём подтверждения...")
            time.sleep(4)

        print("\nГотово! Проверь трек на странице своего профиля SoundCloud.")

        if keep_open:
            input("Браузер оставлен открытым — нажми Enter, чтобы закрыть его... ")

        try:
            context.close()
        except Exception:
            pass  # окно уже закрыто вручную — не страшно, трек к этому моменту уже отправлен


def main():
    parser = argparse.ArgumentParser(description="Загрузка трека на SoundCloud через браузер")
    parser.add_argument("file", nargs="?", help="путь к аудиофайлу")
    parser.add_argument("--title", help="название трека")
    parser.add_argument("--private", action="store_true", help="сделать трек приватным")
    parser.add_argument("--tags", default="", help="теги через пробел, в кавычках")
    parser.add_argument("--description", default="", help="описание трека")
    parser.add_argument("--login", action="store_true", help="только залогиниться и сохранить сессию")
    parser.add_argument("--no-close", dest="keep_open", action="store_true", help="не закрывать браузер сразу")
    args = parser.parse_args()

    if args.login:
        do_login()
        return

    if not args.file:
        parser.error("укажи путь к файлу трека (или запусти с --login для первого раза)")
    if not args.title:
        parser.error("укажи --title \"Название трека\"")

    upload_track(
        file_path=args.file,
        title=args.title,
        private=args.private,
        tags=args.tags,
        description=args.description,
        keep_open=args.keep_open,
    )


if __name__ == "__main__":
    main()
