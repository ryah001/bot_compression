import os
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("7422606069:AAFNBAsE4yUAIlZN1XZRwUsh7wN8TY7PZbU")  # Configure sur Render


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envoyez-moi une vidéo ou un audio.")


# --- FONCTIONS DE TRAITEMENT -------------------------------------

async def compress_video(input_path, output_path):
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-vcodec", "libx264",
        "-crf", "28",        # taux de compression
        "-preset", "medium",
        "-acodec", "aac",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


async def convert_to_audio(input_path, output_path):
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-vn",
        "-acodec", "mp3",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


async def compress_audio(input_path, output_path):
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-b:a", "96k",  # compression audio
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# --- RECEPTION DE FICHIERS ----------------------------------------

async def file_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.video or message.document and message.document.mime_type.startswith("video"):
        # Vidéo détectée
        file_obj = message.video or message.document

        file_id = file_obj.file_id
        context.user_data["last_file_id"] = file_id

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Compresser le fichier", callback_data="compress_video"),
                InlineKeyboardButton("Convertir en Audio", callback_data="convert_audio")
            ]
        ])

        await message.reply_text(
            "Que voulez-vous que je fasse avec ce fichier ?",
            reply_markup=keyboard
        )

    elif message.audio or message.voice or message.document and message.document.mime_type.startswith("audio"):
        # Audio détecté → compression automatique
        file_obj = message.audio or message.voice or message.document
        file = await file_obj.get_file()

        input_path = "input_audio"
        output_path = "compressed_audio.mp3"

        await file.download_to_drive(input_path)
        await compress_audio(input_path, output_path)

        await message.reply_audio(audio=open(output_path, "rb"), caption="Voici l’audio compressé.")

        os.remove(input_path)
        os.remove(output_path)


# --- GESTION DES BOUTONS ------------------------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    file_id = context.user_data.get("last_file_id")
    if not file_id:
        await query.edit_message_text("Aucun fichier détecté.")
        return

    file = await context.bot.get_file(file_id)
    input_path = "input_video"
    await file.download_to_drive(input_path)

    if query.data == "compress_video":
        output_path = "compressed_video.mp4"
        await query.edit_message_text("Compression en cours...")
        await compress_video(input_path, output_path)

        await query.message.reply_video(video=open(output_path, "rb"),
                                        caption="Voici la vidéo compressée.")

        os.remove(input_path)
        os.remove(output_path)

    elif query.data == "convert_audio":
        output_path = "converted_audio.mp3"
        await query.edit_message_text("Conversion en cours...")
        await convert_to_audio(input_path, output_path)

        await query.message.reply_audio(audio=open(output_path, "rb"),
                                        caption="Voici l’audio extrait.")

        os.remove(input_path)
        os.remove(output_path)


# --- KEEP-ALIVE POUR UPTIMEROBOT ---------------------------------

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot opérationnel.")


# --- MAIN ----------------------------------------------------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))

    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO | filters.AUDIO | filters.VOICE,
                                   file_received))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
