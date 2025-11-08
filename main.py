import os
from flask import Flask, request
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import ffmpeg

TOKEN = "8582663417:AAGUfSsfbUACYSJj8qN19Cu1-eNDgHH0d5c"

# --- Serveur Flask pour keep-alive ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot actif", 200

def run():
    app.run(host="0.0.0.0", port=8080)

# --- Fonctions Telegram ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Envoie-moi un fichier vidéo ou audio.")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document or update.message.video or update.message.audio or update.message.voice

    if not file:
        await update.message.reply_text("Fichier non reconnu.")
        return

    file_type = file.mime_type or ""
    file_obj = await file.get_file()
    file_name = file.file_name or "input.mp4"

    os.makedirs("downloads", exist_ok=True)
    input_path = f"downloads/{file_name}"
    await file_obj.download_to_drive(input_path)

    if "video" in file_type:
        keyboard = [
            [InlineKeyboardButton("🎞️ Compresser", callback_data=f"compress:{input_path}")],
            [InlineKeyboardButton("🎧 Convertir en audio", callback_data=f"audio:{input_path}")]
        ]
        await update.message.reply_text(
            "Que voulez-vous faire avec ce fichier ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif "audio" in file_type:
        await update.message.reply_text("Compression audio en cours...")
        output_path = await compress_audio(input_path)
        await update.message.reply_audio(audio=open(output_path, "rb"))
        os.remove(input_path)
        os.remove(output_path)

async def compress_video(input_path: str) -> str:
    output_path = input_path.replace(".", "_compressed.")
    stream = ffmpeg.input(input_path)
    stream = ffmpeg.output(stream, output_path, vcodec='libx264', crf=28, preset='medium')
    ffmpeg.run(stream, overwrite_output=True)
    return output_path

async def convert_to_audio(input_path: str) -> str:
    output_path = input_path.rsplit(".", 1)[0] + ".mp3"
    stream = ffmpeg.input(input_path)
    stream = ffmpeg.output(stream, output_path, acodec='libmp3lame', audio_bitrate='128k')
    ffmpeg.run(stream, overwrite_output=True)
    return output_path

async def compress_audio(input_path: str) -> str:
    output_path = input_path.replace(".", "_compressed.")
    stream = ffmpeg.input(input_path)
    stream = ffmpeg.output(stream, output_path, audio_bitrate='64k')
    ffmpeg.run(stream, overwrite_output=True)
    return output_path

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, path = query.data.split(":", 1)
    if action == "compress":
        await query.edit_message_text("Compression vidéo en cours...")
        output = await compress_video(path)
        await query.message.reply_video(video=open(output, "rb"))
    elif action == "audio":
        await query.edit_message_text("Conversion en audio...")
        output = await convert_to_audio(path)
        await query.message.reply_audio(audio=open(output, "rb"))

    os.remove(path)
    os.remove(output)

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO | filters.AUDIO | filters.VOICE, handle_file))
    application.add_handler(CallbackQueryHandler(button_handler))

    Thread(target=run).start()  # Lance Flask en parallèle
    print("Bot en cours d’exécution...")
    application.run_polling()

if __name__ == "__main__":
    main()

