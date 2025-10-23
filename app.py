from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, send
from flask_mail import Mail, Message
import json
import datetime
import difflib
import random

app = Flask(__name__)
app.secret_key = "secret123"
socketio = SocketIO(app)

# إعدادات البريد
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'fysl20515@gmail.com'  # ← بريدك الحقيقي
app.config['MAIL_PASSWORD'] = 'hyycvpgxpbciubcb'      # ← كلمة مرور التطبيق بدون مسافات

mail = Mail(app)

# تحميل الردود المحفوظة من ملف responses.json
with open("responses.json", "r", encoding="utf-8") as f:
    responses = json.load(f)

# صفحة تسجيل الدخول (تطلب البريد فقط لإرسال كود)
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        code = str(random.randint(100000, 999999))
        session["verify_code"] = code
        session["email"] = email

        msg = Message("كود التحقق", sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"كود التحقق الخاص بك هو: {code}"
        try:
            mail.send(msg)
        except Exception as e:
            return f"حدث خطأ أثناء إرسال البريد: {e}"

        return render_template("verify.html", email=email)

    return render_template("login.html")

# صفحة التحقق من الكود
@app.route("/verify", methods=["POST"])
def verify():
    user_code = request.form.get("code")
    if user_code == session.get("verify_code"):
        session["username"] = session["email"].split("@")[0]
        return redirect(url_for("chat"))
    else:
        return render_template("verify.html", email=session["email"], error="الكود غير صحيح، حاول مرة أخرى")

# صفحة الدردشة
@app.route("/chat")
def chat():
    if "email" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html", username=session["username"])

# وظيفة إيجاد أقرب رد بناءً على الجملة (مطابقة تقريبية + جزئية)
def find_best_match(message):
    message = message.strip().lower()
    keys = list(responses.keys())

    # أولاً نحاول المطابقة التقريبية
    match = difflib.get_close_matches(message, keys, n=1, cutoff=0.4)
    if match:
        return responses[match[0]]

    # لو مفيش تطابق تقريبي، نجرب تطابق جزئي
    for key in keys:
        if key in message or message in key:
            return responses[key]

    return "ممم... مش فاهم قصدك، ممكن توضح أكتر؟ 🤔"

# استقبال الرسائل والرد + حفظ المحادثة
@socketio.on("message")
def handle_message(msg):
    reply = find_best_match(msg)

    try:
        with open("chat_log.txt", "a", encoding="utf-8") as log:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user_email = session.get("email", "مستخدم مجهول")
            log.write(f"[{timestamp}] 👤 {user_email}:\n{msg}\n🤖 البوت:\n{reply}\n\n")
    except Exception as e:
        print("❌ خطأ في حفظ المحادثة:", e)

    send(reply)

if __name__ == "__main__":
    socketio.run(app, debug=True)