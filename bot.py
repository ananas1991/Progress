import os
import math
import asyncio
import logging
import sqlite3
import time
import json
import argparse
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from i18n import get_translator

# =====================
# Database Setup
# =====================
DB_FILE = 'jobs.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            post_text TEXT,
            media TEXT,
            duration INTEGER NOT NULL,
            start_time INTEGER NOT NULL,
            status TEXT DEFAULT 'active'
        )
    ''')
    # Ensure the status column exists for older DBs
    cursor.execute("PRAGMA table_info(jobs)")
    cols = [r[1] for r in cursor.fetchall()]
    if 'status' not in cols:
        cursor.execute("ALTER TABLE jobs ADD COLUMN status TEXT DEFAULT 'active'")
    conn.commit()
    conn.close()


# =====================
# Configuration Settings
# =====================
# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
# Progress bar settings
BAR_LENGTH = 20              # Total characters in the progress bar
DESIRED_INTERVAL = 6.0       # Desired seconds between edits
DELETE_DELAY = 1          # Seconds to wait before deleting final post

# Conversation states
POST, TIME = range(2)

T = None  # Translator is set from CLI in __main__



def generate_progress_bar(progress: int) -> str:
    """
    Generate a text-based progress bar.
    :param progress: Completion percentage (0-100)
    :return: Formatted progress bar string
    """
    percent = int(progress)
    filled = int(percent / 100 * BAR_LENGTH)
    bar = '█' * filled + '░' * (BAR_LENGTH - filled)
    return f'[{bar}] {percent}%'

 



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a short welcome with commands and how to start."""
    await update.message.reply_text(T.start_message, parse_mode='Markdown')


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /run: ask the user for the post content."""
    await update.message.reply_text(T.run_prompt)
    return POST


async def receive_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the post content or media and ask for a duration selection."""
    msg = update.message
    # Handle photo posts (with optional caption)
    if msg.photo:
        # choose highest resolution
        file_id = msg.photo[-1].file_id
        context.user_data['media'] = {'type': 'photo', 'file_id': file_id}
        context.user_data['post_text'] = msg.caption or ''
    else:
        context.user_data['media'] = None
        context.user_data['post_text'] = msg.text or ''

    keyboard = [
        [InlineKeyboardButton(T.min_label(1), callback_data="60"),
         InlineKeyboardButton(T.min_label(5), callback_data="300")],
        [InlineKeyboardButton(T.min_label(10), callback_data="600"),
         InlineKeyboardButton(T.custom_label, callback_data="custom")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await msg.reply_text(T.duration_prompt, reply_markup=reply_markup)
    return TIME


async def time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the duration selection from inline keyboard."""
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'custom':
        await query.edit_message_text(T.custom_duration_prompt)
        return TIME

    duration = int(data)
    context.user_data['duration'] = duration
    await query.edit_message_text(T.scheduled_in_minutes(duration // 60))
    asyncio.create_task(
        run_progress(
            context.bot,
            context.user_data['post_text'],
            context.user_data['media'],
            duration
        )
    )
    return ConversationHandler.END


async def custom_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle a custom duration sent by the user (in minutes)."""
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text(T.custom_duration_invalid)
        return TIME
    minutes = int(text)
    duration = minutes * 60
    context.user_data['duration'] = duration
    await update.message.reply_text(T.scheduled_in_minutes(minutes))
    asyncio.create_task(
        run_progress(
            context.bot,
            context.user_data['post_text'],
            context.user_data['media'],
            duration
        )
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Allow the user to cancel the operation."""
    await update.message.reply_text(T.cancel_op)
    return ConversationHandler.END


async def cancel_job_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show active jobs with inline keyboard to select which one to cancel."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, post_text, start_time, duration FROM jobs WHERE status = 'active'")
    jobs = cursor.fetchall()
    conn.close()
    
    if not jobs:
        await update.message.reply_text(T.no_active_jobs)
        return
    
    keyboard = []
    for job_id, post_text, start_time, duration in jobs:
        # Calculate progress and time remaining
        elapsed = time.time() - start_time
        progress = min(int((elapsed / duration) * 100), 100)
        remaining = max(duration - elapsed, 0)
        time_left_str = format_time_left(remaining)
        
        # Truncate post text for button display
        display_text = (post_text[:30] + '...') if len(post_text) > 30 else post_text
        if not display_text.strip():
            display_text = T.media_post_label
        
        button_text = f"{display_text} ({progress}% - {time_left_str})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"cancel_job_{job_id}")])
    
    keyboard.append([InlineKeyboardButton(T.cancel_selection_label, callback_data="cancel_selection")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(T.select_job_to_cancel, reply_markup=reply_markup)


async def handle_job_cancellation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the job cancellation callback from inline keyboard."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_selection":
        await query.edit_message_text(T.cancellation_cancelled)
        return
    
    if query.data.startswith("cancel_job_"):
        job_id = int(query.data.split("_")[2])
        
        # Get job details before marking as cancelled
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, message_id, post_text FROM jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        
        if job:
            chat_id, message_id, post_text = job
            # Mark as cancelled; the running task will stop on next tick
            cursor.execute("UPDATE jobs SET status = 'cancelled' WHERE id = ?", (job_id,))
            conn.commit()
            
            # Try to delete the progress bar message
            try:
                await context.bot.delete_message(
                    chat_id=chat_id,
                    message_id=message_id
                )
            except Exception:
                pass
            
            display_text = (post_text[:50] + '...') if len(post_text) > 50 else post_text
            if not display_text.strip():
                display_text = T.media_post_label
            await query.edit_message_text(T.job_cancelled_text(display_text))
        else:
            await query.edit_message_text(T.job_not_found)
        
        conn.close()


async def check_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check channel access with verified, non-contradictory results."""
    if not CHANNEL_ID:
        await update.message.reply_text(T.no_channel_configured)
        return

    try:
        # Get chat and membership
        chat = await context.bot.get_chat(CHANNEL_ID)
        member = await context.bot.get_chat_member(CHANNEL_ID, context.bot.id)

        role = member.status.title()
        is_admin = member.status == "administrator"

        # Raw flags (may be missing/irrelevant depending on chat type)
        can_post_flag = bool(getattr(member, "can_post_messages", False)) if is_admin else False
        can_edit_flag = bool(getattr(member, "can_edit_messages", False)) if is_admin else False
        can_delete_flag = bool(getattr(member, "can_delete_messages", False)) if is_admin else False

        # Live tests (verified capabilities)
        send_ok, send_err = False, None
        edit_ok, edit_err = None, None  # None = not attempted yet
        delete_ok, delete_err = None, None
        test_msg = None
        try:
            test_msg = await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=T.test_message_text
            )
            send_ok = True
        except Exception as e:
            send_err = str(e)

        if send_ok and test_msg is not None:
            # Try edit
            try:
                await context.bot.edit_message_text(
                    chat_id=CHANNEL_ID,
                    message_id=test_msg.message_id,
                    text="✏️ Edit test — ok"
                )
                edit_ok = True
            except Exception as e:
                edit_ok = False
                edit_err = str(e)

            # Try delete
            try:
                await context.bot.delete_message(CHANNEL_ID, test_msg.message_id)
                delete_ok = True
            except Exception as e:
                delete_ok = False
                delete_err = str(e)

        # Compute readiness and next steps (use verified tests first)
        ready = bool(send_ok) and bool(edit_ok)
        steps = []
        if not is_admin:
            steps.append(T.step_add_admin)
        if send_ok is False:
            if is_admin and not can_post_flag:
                steps.append(T.step_grant_post)
            steps.append(T.step_ensure_channel_id)
        if edit_ok is False:
            if is_admin and not can_edit_flag:
                steps.append(T.step_grant_edit)
            else:
                steps.append(T.step_allow_edit_own)
        if delete_ok is False:
            if is_admin and not can_delete_flag:
                steps.append(T.step_grant_delete)

        # Build clear, non-contradictory report
        lines = []
        lines.append(T.access_check_title)
        lines.append("")
        lines.append(f"🏢 {T.channel_label}: {chat.title} ({CHANNEL_ID})")
        lines.append(f"🤖 {T.role_label}: {role}")
        lines.append("")
        lines.append(T.capabilities_verified_title)
        lines.append(f"- {T.send_messages_label}: {'✅ Verified' if send_ok else f'❌ Failed — {send_err}'}")
        if send_ok:
            lines.append(f"- {T.edit_messages_label}: {'✅ Verified' if edit_ok else f'❌ Failed — {edit_err}'}")
            # Deleting is optional
            if delete_ok is True:
                lines.append(f"- {T.delete_messages_label}: ✅ Verified ({T.optional_word})")
            elif delete_ok is False:
                lines.append(f"- {T.delete_messages_label}: ⚠️ Failed ({T.optional_word}) — {delete_err}")
            else:
                lines.append(f"- {T.delete_messages_label}: ⚠️ Skipped ({T.optional_word})")
        else:
            lines.append(f"- {T.edit_messages_label}: ⚠️ Skipped")
            lines.append(f"- {T.delete_messages_label}: ⚠️ Skipped ({T.optional_word})")
        lines.append("")
        if ready:
            lines.append(T.ready_message)
        else:
            lines.append(T.action_needed_label)
            for step in steps:
                lines.append(f"- {step}")

        await update.message.reply_text("\n".join(lines), parse_mode='Markdown')

    except Exception as e:
        error_msg = str(e)
        if "chat not found" in error_msg.lower():
            await update.message.reply_text(
                T.channel_not_found_steps_template.format(channel_id=CHANNEL_ID)
            )
        elif "not enough rights" in error_msg.lower():
            await update.message.reply_text(
                T.insufficient_rights_template.format(channel_id=CHANNEL_ID)
            )
        else:
            await update.message.reply_text(
                T.generic_error_template.format(error=error_msg, channel_id=CHANNEL_ID)
            )


def add_job_to_db(chat_id, message_id, post_text, media, duration, start_time):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (chat_id, message_id, post_text, media, duration, start_time, status) VALUES (?, ?, ?, ?, ?, ?, 'active')",
        (chat_id, message_id, post_text, json.dumps(media), duration, start_time)
    )
    conn.commit()
    job_id = cursor.lastrowid
    conn.close()
    return job_id

def remove_job_from_db(job_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

def get_job_status(job_id: int) -> str:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


async def run_progress(bot, post_text: str, media: dict, duration: float, job_id: int = None, message_id: int = None, start_time: int = None) -> None:
    """
    Run the progress bar in the target channel, then post the content.
    :param bot: Telegram Bot instance
    :param post_text: The content to post after the bar completes
    :param media: Optional media dict ({'type','file_id'})
    :param duration: Total duration for the bar in seconds
    :param job_id: The job ID from the database
    :param message_id: The message ID of the progress bar message
    :param start_time: The start time of the progress bar
    """
    # If resuming, calculate elapsed time
    if start_time:
        elapsed = time.time() - start_time
        if elapsed >= duration:
            # Job should have already finished
            remove_job_from_db(job_id)
            return
    else:
        elapsed = 0
        start_time = time.time()

    # Compute steps based on DESIRED_INTERVAL and enforce integer percent
    steps = max(int(duration / DESIRED_INTERVAL), 1)
    approx_step = 100 / steps
    if approx_step < 1:
        # too many steps, use 1% increments
        step_pct = 1
        total_steps = 100
        interval = duration / total_steps
    else:
        step_pct = math.floor(approx_step)
        total_steps = math.ceil(100 / step_pct)
        interval = duration / total_steps
    
    if not message_id:
        # Send initial progress bar
        message = await bot.send_message(
            chat_id=CHANNEL_ID,
            text=generate_progress_bar(0)
        )
        message_id = message.message_id
        job_id = add_job_to_db(CHANNEL_ID, message_id, post_text, media, duration, start_time)
    
    progress = int((elapsed / duration) * 100)
    seconds_left = max(duration - elapsed, 0)
    time_left_str = T.format_time_left(seconds_left)

    while elapsed < duration:
        await asyncio.sleep(interval)

        # Check for cancellation before attempting to edit
        status = get_job_status(job_id)
        if status is None or status == 'cancelled':
            # Clean up and exit gracefully
            try:
                await bot.delete_message(chat_id=CHANNEL_ID, message_id=message_id)
            except Exception:
                pass
            if status is not None:
                remove_job_from_db(job_id)
            return

        elapsed += interval
        progress = min(progress + step_pct, 100)
        new_seconds_left = max(duration - elapsed, 0)

        update_time = False
        # Time is displayed in days and hours, update every hour
        if seconds_left > 24 * 60 * 60:
            if math.floor(seconds_left / 3600) != math.floor(new_seconds_left / 3600):
                update_time = True
        # Time is displayed in hours and minutes, or just minutes, update every minute
        elif seconds_left > 60:
            if math.floor(seconds_left / 60) != math.floor(new_seconds_left / 60):
                update_time = True
        # Less than a minute, update with the progress bar
        else:
            update_time = True

        if update_time:
            time_left_str = T.format_time_left(new_seconds_left)

        seconds_left = new_seconds_left

        bar_text = (
            f"{generate_progress_bar(progress)}\n"
            f"{time_left_str} {T.remaining_text}"
        )

        try:
            await bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=message_id,
                text=bar_text
            )
        except Exception as e:
            logging.warning(f"Edit failed: {e}")

    # Remove the progress bar message
    try:
        await bot.delete_message(
            chat_id=CHANNEL_ID,
            message_id=message_id
        )
    except Exception:
        pass
    
    remove_job_from_db(job_id)

    # Send the final post (text or photo)
    if media and media.get('type') == 'photo':
        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=media['file_id'],
            caption=post_text or None
        )
    else:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=post_text
        )


async def resume_jobs(app):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, chat_id, message_id, post_text, media, duration, start_time FROM jobs WHERE status = 'active'")
    jobs = cursor.fetchall()
    conn.close()

    for job in jobs:
        job_id, chat_id, message_id, post_text, media, duration, start_time = job
        media_dict = json.loads(media)
        asyncio.create_task(
            run_progress(app.bot, post_text, media_dict, duration, job_id, message_id, start_time)
        )

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler('run', run_command)],
        states={
            POST: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_post)],
            TIME: [
                CallbackQueryHandler(time_selection),
                MessageHandler(filters.TEXT & ~filters.COMMAND, custom_time_input),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('cancel', cancel_job_command))
    app.add_handler(CommandHandler('check_add', check_add_command))
    app.add_handler(CallbackQueryHandler(handle_job_cancellation, pattern=r"^(cancel_job_\d+|cancel_selection)$"))
    app.add_handler(conv)
    
    await app.initialize()
    await resume_jobs(app)
    await app.start()
    await app.updater.start_polling()
    
    # Keep the bot running
    while True:
        await asyncio.sleep(3600) # Keep alive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Progresser Bot')
    parser.add_argument('--language', '-l', default='ru', choices=['ru', 'en'], help='Interface language (default: ru)')
    args = parser.parse_args()

    # Initialize translator before starting the bot
    T = get_translator(args.language)

    asyncio.run(main())
