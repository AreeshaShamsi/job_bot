import os
import json
import smtplib
import ssl
from email.message import EmailMessage

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# ===== CONFIG =====
BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "areeshashamsi11@gmail.com"
SMTP_PASS = "YOUR_APP_PASSWORD"

DATA_DIR = "data"
RESUME_DIR = os.path.join(DATA_DIR, "resumes")
USERS_DB = os.path.join(DATA_DIR, "users.json")

REG_NAME, REG_EMAIL, REG_PHONE, UPLOAD_RESUME = range(4)

# ===== SETUP =====
def setup():
    os.makedirs(RESUME_DIR, exist_ok=True)
    if not os.path.exists(USERS_DB):
        with open(USERS_DB, "w") as f:
            json.dump({}, f)

def load_users():
    with open(USERS_DB, "r") as f:
        return json.load(f)

def save_users(data):
    with open(USERS_DB, "w") as f:
        json.dump(data, f, indent=2)

# ===== REGISTER =====
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter your name:")
    return REG_NAME

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Enter your email:")
    return REG_EMAIL

async def register_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text
    await update.message.reply_text("Enter your phone:")
    return REG_PHONE

async def register_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    users = load_users()
    users[chat_id] = {
        "name": context.user_data["name"],
        "email": context.user_data["email"],
        "phone": update.message.text,
        "resume": ""
    }
    save_users(users)

    await update.message.reply_text("✅ Registered! Now upload resume using /uploadresume")
    return ConversationHandler.END

# ===== UPLOAD RESUME =====
async def upload_resume_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Send your resume (PDF)")
    return UPLOAD_RESUME

async def upload_resume_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    if not update.message.document:
        await update.message.reply_text("❌ Please send a file")
        return UPLOAD_RESUME

    doc = update.message.document
    file = await doc.get_file()

    path = f"{RESUME_DIR}/{chat_id}.pdf"
    await file.download_to_drive(path)

    users = load_users()
    users[chat_id]["resume"] = path
    save_users(users)

    await update.message.reply_text("✅ Resume uploaded successfully!")
    return ConversationHandler.END

# ===== SEND EMAIL (UPDATED BODY) =====
async def send_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = str(update.effective_chat.id)
        users = load_users()
        user = users.get(chat_id)

        if not user or not user.get("resume"):
            await update.message.reply_text("❌ Register and upload resume first")
            return

        text = update.message.text

        if "," not in text:
            await update.message.reply_text("❌ Format: email,company,role")
            return

        parts = text.split(",")
        email = parts[0].strip()
        company = parts[1].strip()
        role = parts[2].strip() if len(parts) > 2 else "the role"

        msg = EmailMessage()
        msg['From'] = SMTP_USER
        msg['To'] = email
        msg['Subject'] = f"Application for {role}"

        body = f"""
Hello {company},

My name is {user['name']} and I am very interested in the {role} role at your company. I believe my skills and experience make me a strong fit, and I would love the opportunity to contribute. Please find my resume attached for your review.

Thank you for your time and consideration. I look forward to hearing from you.

Best regards,  
{user['name']}  
{user['email']}  
{user['phone']}
"""
        msg.set_content(body)

        with open(user["resume"], "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="octet-stream",
                filename="resume.pdf"
            )

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        await update.message.reply_text("✅ Email sent successfully!")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ===== MAIN =====
def main():
    setup()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    reg = ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            REG_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_email)],
            REG_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_phone)],
        },
        fallbacks=[]
    )

    upload_conv = ConversationHandler(
        entry_points=[CommandHandler("uploadresume", upload_resume_start)],
        states={
            UPLOAD_RESUME: [
                MessageHandler(filters.Document.ALL, upload_resume_file)
            ],
        },
        fallbacks=[]
    )

    app.add_handler(reg)
    app.add_handler(upload_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_email))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()