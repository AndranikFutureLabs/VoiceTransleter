import asyncio
import flet as ft
from pathlib import Path
import os
import subprocess
import logging
import tkinter as tk
from tkinter import filedialog
import threading

(Path(__file__).parent / "temp").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent / "temp" / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

from config import TEMP_DIR
from voice_transleter.pipeline import dub_video
from voice_transleter.voice_cloner import get_voice_profiles, clone_voice
from voice_transleter.tts import synthesize_text, is_xtts_downloaded, download_xtts


def _pick_file_dialog(title: str, filetypes: list) -> str | None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()
    return path if path else None


def main(page: ft.Page):
    page.title = "VoiceTransleter"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 24
    page.window_width = 1000
    page.window_height = 750
    page.window_min_width = 800
    page.window_min_height = 600
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ft.Colors.CYAN_400,
            secondary=ft.Colors.AMBER_400,
            surface=ft.Colors.GREY_900,
        ),
        use_material3=True,
    )
    def _make_link(text: str, url: str):
        return ft.Text(spans=[ft.TextSpan(text, url=url)], size=13)

    def _show_about(_):
        dlg = ft.AlertDialog(
            title=ft.Text("О программе"),
            content=ft.Column([
                ft.Text("VoiceTransleter — дубляж видео с переводом", size=14),
                ft.Divider(),
                ft.Text("Разработчик: Андраник Алавердян (AndranikFutureLabs)", size=13),
                _make_link("Поддержка: @AndranikFutureLabs", "https://t.me/AndranikFutureLabs"),
                _make_link("Канал разработчика: @AndranikFutureLabsChannel", "https://t.me/AndranikFutureLabsChannel"),
                _make_link("Сайт: https://andranik-future-labs.ru", "https://andranik-future-labs.ru"),
                _make_link("GitHub: https://github.com/AndranikFutureLabs/VoiceTransleter", "https://github.com/AndranikFutureLabs/VoiceTransleter"),
                ft.Divider(),
                ft.Text("Версия 1.1", size=12, color=ft.Colors.GREY_400),
            ], width=480, height=300, spacing=8, scroll=ft.ScrollMode.AUTO),
            actions=[ft.TextButton("Закрыть", on_click=lambda _: page.pop_dialog())],
        )
        page.show_dialog(dlg)

    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.RECORD_VOICE_OVER, color=ft.Colors.CYAN_400),
        title=ft.Text("VoiceTransleter", weight=ft.FontWeight.BOLD, size=22),
        center_title=False,
        bgcolor=ft.Colors.GREY_900,
        actions=[
            ft.IconButton(ft.Icons.INFO_OUTLINE, tooltip="О программе", on_click=_show_about),
        ],
    )

    selected_video = {"path": None}
    clone_file_path = {"path": None}
    voices = get_voice_profiles()
    is_running = {"val": False}
    xtts_ready = {"val": is_xtts_downloaded()}
    xtts_downloading = {"val": False}

    # --- UI controls ---
    file_info = ft.Text(size=14, color=ft.Colors.GREY_300, visible=False)

    drop_zone = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.UPLOAD_FILE, size=48, color=ft.Colors.CYAN_300),
            ft.Text("Нажмите для выбора видеофайла", size=16),
            ft.Text("MP4, AVI, MKV, MOV, WebM", size=12, color=ft.Colors.GREY_400),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        height=140, border_radius=16, bgcolor=ft.Colors.GREY_800,
        border=ft.Border(
            left=ft.BorderSide(2, ft.Colors.CYAN_700),
            top=ft.BorderSide(2, ft.Colors.CYAN_700),
            right=ft.BorderSide(2, ft.Colors.CYAN_700),
            bottom=ft.BorderSide(2, ft.Colors.CYAN_700),
        ),
        ink=True,
        on_click=lambda e: _on_pick_video(),
    )

    src_lang = ft.Dropdown(
        label="Язык оригинала", value="en",
        options=[ft.dropdown.Option("en", "Английский")], width=200,
    )

    voice_dropdown = ft.Dropdown(label="Голос дубляжа", width=300)

    def refresh_voices():
        nonlocal voices
        voices = get_voice_profiles()
        opts = []
        for v in voices:
            label = v["name"] + (" ⭐" if v.get("engine") == "xtts" else "")
            opts.append(ft.dropdown.Option(v["id"], label))
        voice_dropdown.options = opts
        if opts:
            voice_dropdown.value = voices[0]["id"]
        page.update()

    refresh_voices()

    voice_preview_btn = ft.Button(
        "Прослушать", icon=ft.Icons.VOLUME_UP,
        style=ft.ButtonStyle(color=ft.Colors.CYAN_300, bgcolor=ft.Colors.GREY_700),
        on_click=lambda e: _preview_voice(),
    )

    status_log = ft.ListView(expand=True, spacing=4, auto_scroll=True)
    status_box = ft.Container(
        content=status_log, height=180,
        bgcolor=ft.Colors.GREY_800, border_radius=12, padding=12, visible=False,
    )

    progress_bar = ft.ProgressBar(
        width=600, color=ft.Colors.CYAN_400, bgcolor=ft.Colors.GREY_700, visible=False,
    )

    start_btn = ft.Button(
        "Начать дубляж", icon=ft.Icons.PLAY_ARROW, disabled=True,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE, bgcolor=ft.Colors.CYAN_600,
            padding=ft.Padding(left=32, right=32, top=16, bottom=16),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
        on_click=lambda e: _run_pipeline(),
    )

    download_xtts_btn = ft.Button(
        "XTTS загружен" if xtts_ready["val"] else "Загрузить XTTS",
        icon=ft.Icons.DOWNLOAD,
        disabled=xtts_ready["val"] or xtts_downloading["val"],
        style=ft.ButtonStyle(color=ft.Colors.CYAN_300, bgcolor=ft.Colors.GREY_700),
        on_click=lambda e: _download_xtts(),
    )

    page.add(
        ft.Text("Дубляж видео", size=18, weight=ft.FontWeight.BOLD),
        ft.Text("Перевод английской речи в русскую с синтезом голоса",
                size=13, color=ft.Colors.GREY_400),
        ft.Container(height=16),
        drop_zone, file_info, ft.Container(height=20),
        ft.Row([
            src_lang,
            ft.Container(content=voice_dropdown, expand=True),
            voice_preview_btn,
            ft.Button("Клонировать голос", icon=ft.Icons.PERSON_ADD,
                      style=ft.ButtonStyle(color=ft.Colors.AMBER_300, bgcolor=ft.Colors.GREY_800),
                      on_click=lambda e: _open_clone_dialog()),
            download_xtts_btn,
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.END),
        ft.Container(height=24),
        ft.Row([start_btn], alignment=ft.MainAxisAlignment.CENTER),
        ft.Container(height=16), progress_bar, status_box,
    )

    # --- helpers ---
    def log(msg):
        color = ft.Colors.GREY_300
        if "❌" in msg or "Error" in msg or "Ошибка" in msg:
            color = ft.Colors.RED_300
        elif "✅" in msg or "Done" in msg or "Готово" in msg:
            color = ft.Colors.GREEN_300
        elif "[" in msg:
            color = ft.Colors.CYAN_300
        status_log.controls.append(ft.Text(msg, size=12, color=color, font_family="monospace"))
        page.update()

    def snack(msg):
        sb = ft.SnackBar(content=ft.Text(msg), duration=3000)
        page.show_dialog(sb)

    def show_result(result_path):
        card = ft.Container(
            content=ft.Column([
                ft.Text("Готово!", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                ft.Text(f"Файл: {Path(result_path).name}", size=13, color=ft.Colors.GREY_300),
                ft.Row([
                    ft.Button("Открыть видео", icon=ft.Icons.OPEN_IN_NEW,
                              on_click=lambda _: os.startfile(str(result_path)),
                              style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.CYAN_600)),
                    ft.Button("Открыть папку", icon=ft.Icons.FOLDER_OPEN,
                              on_click=lambda _: os.startfile(str(Path(result_path).parent)),
                              style=ft.ButtonStyle(color=ft.Colors.CYAN_300, bgcolor=ft.Colors.GREY_800)),
                ], spacing=12),
            ]),
            padding=20, border_radius=12, bgcolor=ft.Colors.GREY_800,
            margin=ft.Margin(left=0, right=0, top=12, bottom=0),
        )
        page.add(card)
        page.update()

    # --- file pick ---
    def _on_pick_video():
        p = _pick_file_dialog("Выберите видеофайл", [("Video", "*.mp4 *.avi *.mkv *.mov *.webm"), ("All", "*.*")])
        if p:
            selected_video["path"] = p
            path = Path(p)
            sz = path.stat().st_size
            sz_str = f"{sz/1024/1024:.1f} MB" if sz > 1048576 else f"{sz/1024:.0f} KB"
            file_info.value = f"Выбрано: {path.name} ({sz_str})"
            file_info.visible = True
            drop_zone.border = ft.Border(
                left=ft.BorderSide(2, ft.Colors.GREEN_400),
                top=ft.BorderSide(2, ft.Colors.GREEN_400),
                right=ft.BorderSide(2, ft.Colors.GREEN_400),
                bottom=ft.BorderSide(2, ft.Colors.GREEN_400),
            )
            start_btn.disabled = False
            page.update()

    # --- preview voice ---
    def _preview_voice():
        vid = voice_dropdown.value
        if not vid:
            return
        voice = next((v for v in voices if v["id"] == vid), None)
        if not voice:
            return
        voice_preview_btn.disabled = True
        page.update()
        threading.Thread(target=_preview_worker, args=(voice,), daemon=True).start()

    def _preview_worker(voice):
        logger.info("Preview start: engine=%s, id=%s", voice.get("engine"), voice.get("id"))
        try:
            audio = synthesize_text("Здравствуйте, это тестовый образец голоса.", voice)
            logger.debug("Audio synthesized: type=%s shape=%s", type(audio).__name__, audio.shape if hasattr(audio, "shape") else "?")
            TEMP_DIR.mkdir(exist_ok=True)
            p = TEMP_DIR / "voice_preview.wav"
            p.unlink(missing_ok=True)
            import soundfile as sf
            import numpy as np
            a = (audio.cpu() if hasattr(audio, 'cpu') else audio).numpy() if hasattr(audio, 'numpy') else audio
            sf.write(str(p), (a * 32767).astype(np.int16), 24000)
            logger.info("Wrote preview to %s (size=%d)", p, p.stat().st_size)
            try:
                subprocess.run(['cmd', '/c', 'start', '', str(p)], check=False, timeout=5)
                logger.info("start command succeeded")
            except Exception as open_err:
                logger.error("Failed to open file: %s", open_err)
                snack(f"Файл сохранён: {p}")
        except Exception as ex:
            logger.exception("Preview error")
            snack(f"Ошибка: {ex}")
        finally:
            voice_preview_btn.disabled = False
            page.update()

    # --- clone dialog ---
    def _open_clone_dialog():
        name_field = ft.TextField(label="Название голоса", hint_text="Например: Голос Ивана")
        file_label = ft.Text("Файл не выбран", size=12, color=ft.Colors.GREY_400)

        def pick_audio(_):
            p = _pick_file_dialog("Выберите аудиообразец", [("Audio", "*.wav *.mp3 *.m4a *.ogg"), ("All", "*.*")])
            if p:
                clone_file_path["path"] = p
                file_label.value = Path(p).name
                file_label.color = ft.Colors.GREEN_300
                page.update()

        def do_clone(_):
            if not clone_file_path["path"]:
                snack("Сначала выберите аудиофайл")
                return
            name = name_field.value or "Мой голос"
            page.pop_dialog()
            snack("Клонирование запущено... (может занять несколько минут)")
            threading.Thread(target=_clone_worker, args=(name,), daemon=True).start()

        dlg = ft.AlertDialog(
            title=ft.Text("Клонирование голоса"),
            content=ft.Column([
                ft.Text("Загрузите аудиообразец (WAV/MP3, 3-10 секунд)", size=13),
                ft.Button("Выбрать аудиофайл", icon=ft.Icons.AUDIO_FILE, on_click=pick_audio),
                file_label, name_field,
            ], width=400, height=220, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: _close_dlg(dlg)),
                ft.Button("Клонировать", on_click=do_clone),
            ],
        )
        page.show_dialog(dlg)

    def _close_dlg(dlg=None):
        page.pop_dialog()

    def _clone_worker(name):
        try:
            result = clone_voice(name, clone_file_path["path"])
            refresh_voices()
            snack(f"Голос '{result['name']}' создан!")
        except Exception as ex:
            snack(f"Ошибка: {ex}")

    # --- download xtts ---
    def _download_xtts():
        if xtts_downloading["val"]:
            return
        xtts_downloading["val"] = True
        download_xtts_btn.disabled = True
        download_xtts_btn.text = "Загрузка..."
        status_log.controls.clear()
        status_box.visible = True
        progress_bar.visible = True
        page.update()
        threading.Thread(target=_download_worker, daemon=True).start()

    def _download_worker():
        try:
            download_xtts(progress_callback=log)
            xtts_ready["val"] = True
            download_xtts_btn.text = "XTTS загружен"
            log("✅ XTTS v2 готова к использованию!")
        except Exception as ex:
            log(f"❌ Ошибка загрузки XTTS: {ex}")
            download_xtts_btn.text = "Загрузить XTTS"
            download_xtts_btn.disabled = False
        finally:
            xtts_downloading["val"] = False
            progress_bar.visible = False
            page.update()

    # --- pipeline ---
    def _run_pipeline():
        if not selected_video["path"] or is_running["val"]:
            return
        is_running["val"] = True
        start_btn.disabled = True
        start_btn.text = "Обработка..."
        progress_bar.visible = True
        status_box.visible = True
        status_log.controls.clear()
        page.update()
        threading.Thread(target=_pipeline_worker, daemon=True).start()

    def _pipeline_worker():
        nonlocal voices
        vid = voice_dropdown.value or "silero_xenia"
        log("Запуск пайплайна дубляжа...")
        try:
            result = dub_video(
                video_path=selected_video["path"],
                source_lang=src_lang.value or "en",
                voice_id=vid,
                progress_callback=log,
            )
            is_running["val"] = False
            start_btn.disabled = False
            start_btn.text = "Начать дубляж"
            progress_bar.visible = False
            log("Готово!")
            show_result(result)
        except Exception as ex:
            is_running["val"] = False
            start_btn.disabled = False
            start_btn.text = "Начать дубляж"
            progress_bar.visible = False
            log(f"Ошибка: {ex}")
            snack(f"Ошибка: {ex}")
        page.update()


if __name__ == "__main__":
    ft.app(target=main)
