import math


class Translator:
    def __init__(self, lang: str):
        self.lang = lang if lang in ("en", "ru") else "ru"

        if self.lang == "en":
            # English messages
            self.start_message = (
                "🤖 Progresser Bot\n\n"
                "Schedule posts to your channel with a live progress bar that counts down until publish.\n\n"
                "📋 Available commands:\n"
                "• `/run` — schedule a new post\n"
                "• `/cancel` — view/cancel active schedules\n"
                "• `/check_add` — verify channel permissions\n\n"
                "👉 Get started: send `/run`"
            )

            self.run_prompt = (
                "📄 Send the content you want to schedule (text, photo, or both)."
            )
            self.duration_prompt = "⏱ Choose how long the progress bar should run:"
            self.custom_label = "Custom"
            self.custom_duration_prompt = (
                "✏️ Send the desired duration in minutes (positive integer)."
            )
            self.custom_duration_invalid = (
                "⚠️ Please send a positive integer for minutes."
            )
            self.cancel_op = "❌ Operation cancelled."
            self.no_active_jobs = "❌ No active jobs to cancel."
            self.select_job_to_cancel = "🗑 Select a job to cancel:"
            self.cancel_selection_label = "❌ Cancel selection"
            self.cancellation_cancelled = "❌ Cancellation cancelled."
            self.job_not_found = "❌ Job not found (may have already completed)."
            self.media_post_label = "[Media post]"
            self.test_message_text = "🤖 Access test — will be edited and deleted"

            # Access check labels
            self.access_check_title = "📊 Channel Access Check"
            self.channel_label = "Channel"
            self.role_label = "Role"
            self.capabilities_verified_title = "Capabilities (verified):"
            self.send_messages_label = "Send Messages"
            self.edit_messages_label = "Edit Messages"
            self.delete_messages_label = "Delete Messages"
            self.optional_word = "optional"
            self.ready_message = "✅ Ready: bot can post and update progress bars."
            self.action_needed_label = "❌ Action needed:"
            self.step_add_admin = "Add the bot as a channel administrator"
            self.step_grant_post = "Grant 'Post Messages'"
            self.step_grant_edit = "Grant 'Edit Messages' (required for progress bar updates)"
            self.step_grant_delete = "Grant 'Delete Messages' (optional, cleans up progress bars)"
            self.step_ensure_channel_id = "Ensure channel ID is correct and posting is allowed"
            self.step_allow_edit_own = "Allow the bot to edit its own channel posts"

            self.no_channel_configured = (
                "⚠️ No channel ID configured in environment variables."
            )
            self.channel_not_found_steps_template = (
                "❌ Bot is not added to the channel {channel_id} or channel doesn't exist.\n\n"
                "📝 Steps:\n"
                "1) Add the bot as a channel administrator\n"
                "2) Grant Post, Edit, and (optional) Delete Messages"
            )
            self.insufficient_rights_template = (
                "❌ Bot lacks sufficient permissions in channel {channel_id}.\n\n"
                "🔑 Required: Post, Edit messages. Optional: Delete messages."
            )
            self.generic_error_template = (
                "❌ Error checking channel access: {error}\n\n"
                "📝 Ensure the bot is added to channel {channel_id} with admin rights."
            )

            # Time words
            self.less_than_a_minute = "<1 minute"
            self.day = "day"
            self.days = "days"
            self.hour = "hour"
            self.hours = "hours"
            self.minute = "minute"
            self.minutes = "minutes"
            self.remaining_text = "remaining until the scheduled post"

        else:
            # Russian messages (default)
            self.start_message = (
                "🤖 Progresser Bot\n\n"
                "Планируйте публикации в канал с живым progress bar до выхода поста.\n\n"
                "📋 Доступные команды:\n"
                "• `/run` — запланировать новый пост\n"
                "• `/cancel` — посмотреть/отменить активные задачи\n"
                "• `/check_add` — проверить права в канале\n\n"
                "👉 Начните с команды `/run`"
            )

            self.run_prompt = (
                "📄 Отправьте содержание для публикации (текст, фото или оба варианта)."
            )
            self.duration_prompt = "⏱ Выберите длительность progress bar:"
            self.custom_label = "Свой вариант"
            self.custom_duration_prompt = (
                "✏️ Отправьте длительность в минутах (целое положительное число)."
            )
            self.custom_duration_invalid = (
                "⚠️ Пожалуйста, отправьте положительное целое число минут."
            )
            self.cancel_op = "❌ Операция отменена."
            self.no_active_jobs = "❌ Нет активных задач для отмены."
            self.select_job_to_cancel = "🗑 Выберите задачу для отмены:"
            self.cancel_selection_label = "❌ Отменить выбор"
            self.cancellation_cancelled = "❌ Отмена прервана."
            self.job_not_found = "❌ Задача не найдена (возможно уже завершена)."
            self.media_post_label = "[Пост с медиа]"
            self.test_message_text = "🤖 Тест доступа — будет отредактировано и удалено"

            # Access check labels
            self.access_check_title = "📊 Проверка доступа к каналу"
            self.channel_label = "Канал"
            self.role_label = "Роль"
            self.capabilities_verified_title = "Возможности (проверено):"
            self.send_messages_label = "Отправка сообщений"
            self.edit_messages_label = "Редактирование сообщений"
            self.delete_messages_label = "Удаление сообщений"
            self.optional_word = "опционально"
            self.ready_message = "✅ Готово: бот может публиковать и обновлять прогресс-бар."
            self.action_needed_label = "❌ Требуются действия:"
            self.step_add_admin = "Добавьте бота администратором канала"
            self.step_grant_post = "Выдайте право «Публиковать сообщения»"
            self.step_grant_edit = "Выдайте право «Редактировать сообщения» (нужно для обновлений прогресса)"
            self.step_grant_delete = "Выдайте право «Удалять сообщения» (опционально; для очистки прогресса)"
            self.step_ensure_channel_id = "Убедитесь, что ID канала верный и публикации разрешены"
            self.step_allow_edit_own = "Разрешите боту редактировать собственные сообщения в канале"

            self.no_channel_configured = (
                "⚠️ Не указан ID канала в переменных окружения."
            )
            self.channel_not_found_steps_template = (
                "❌ Бот не добавлен в канал {channel_id} или канал не существует.\n\n"
                "📝 Шаги:\n"
                "1) Добавьте бота администратором канала\n"
                "2) Выдайте права: Публикация, Редактирование и (опционально) Удаление сообщений"
            )
            self.insufficient_rights_template = (
                "❌ У бота недостаточно прав в канале {channel_id}.\n\n"
                "🔑 Требуются: Публикация, Редактирование. Опционально: Удаление."
            )
            self.generic_error_template = (
                "❌ Ошибка проверки доступа к каналу: {error}\n\n"
                "📝 Убедитесь, что бот добавлен в канал {channel_id} с правами администратора."
            )

            # Time words
            self.less_than_a_minute = "<1 минуты"
            self.day_s = "день"
            self.day_f = "дня"
            self.day_m = "дней"
            self.hour_s = "час"
            self.hour_f = "часа"
            self.hour_m = "часов"
            self.minute_s = "минута"
            self.minute_f = "минуты"
            self.minute_m = "минут"
            self.remaining_text = "осталось до нового поста для дорогих любимых подписчиков 😱"

    # ---------- Common helpers ----------
    def min_label(self, n: int) -> str:
        if self.lang == "en":
            return f"{n} {'minute' if n == 1 else 'minutes'}"
        else:
            # Russian nominative forms for button labels
            if n % 10 == 1 and n % 100 != 11:
                word = "минута"
            elif 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
                word = "минуты"
            else:
                word = "минут"
            return f"{n} {word}"

    def scheduled_in_minutes(self, minutes: int) -> str:
        if self.lang == "en":
            return f"✅ Scheduled! The post will go out in {minutes} {'minute' if minutes == 1 else 'minutes'}."
        else:
            # Accusative after "через": минуту/минуты/минут
            n = abs(minutes)
            if n % 10 == 1 and n % 100 != 11:
                word = "минуту"
            elif 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
                word = "минуты"
            else:
                word = "минут"
            return f"✅ Запланировано! Публикация через {minutes} {word}."

    def job_cancelled_text(self, text: str) -> str:
        return (f"✅ Job cancelled: {text}" if self.lang == "en"
                else f"✅ Задача отменена: {text}")

    # ---------- Time formatting ----------
    def _ru_plural(self, n: int, singular: str, few: str, many: str) -> str:
        n = abs(n)
        if n % 10 == 1 and n % 100 != 11:
            return singular
        elif 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
            return few
        else:
            return many

    def format_time_left(self, seconds: float) -> str:
        if seconds < 60:
            return self.less_than_a_minute if self.lang == "en" else self.less_than_a_minute

        minutes = math.ceil(seconds / 60)
        days = minutes // 1440
        hours = (minutes % 1440) // 60
        mins = minutes % 60

        if self.lang == "en":
            parts = []
            if days > 0:
                parts.append(f"{days} {'day' if days == 1 else 'days'}")
            if hours > 0:
                parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
            if mins > 0 and days == 0:
                parts.append(f"{mins} {'minute' if mins == 1 else 'minutes'}")
            return " ".join(parts)
        else:
            parts = []
            if days > 0:
                parts.append(f"{days} {self._ru_plural(days, self.day_s, self.day_f, self.day_m)}")
            if hours > 0:
                parts.append(f"{hours} {self._ru_plural(hours, self.hour_s, self.hour_f, self.hour_m)}")
            if mins > 0 and days == 0:
                parts.append(f"{mins} {self._ru_plural(mins, self.minute_s, self.minute_f, self.minute_m)}")
            return " ".join(parts)


def get_translator(lang: str) -> Translator:
    return Translator(lang)
