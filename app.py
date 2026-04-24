import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, ConversationHandler
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime

# STATES
(NAME, ADDRESS, ITEM, QTY, RATE, CGST, SGST) = range(7)

user_data_store = {}

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

app = Flask(__name__)

dispatcher = Dispatcher(bot, None, use_context=True)


# -------- HANDLERS --------

def start(update, context):
    update.message.reply_text("Customer Name:")
    return NAME

def name(update, context):
    user_data_store["name"] = update.message.text
    update.message.reply_text("Customer Address:")
    return ADDRESS

def address(update, context):
    user_data_store["address"] = update.message.text
    update.message.reply_text("Item Description:")
    return ITEM

def item(update, context):
    user_data_store["item"] = update.message.text
    update.message.reply_text("Quantity:")
    return QTY

def qty(update, context):
    try:
        user_data_store["qty"] = float(update.message.text)
    except:
        update.message.reply_text("Enter valid number:")
        return QTY
    update.message.reply_text("Rate:")
    return RATE

def rate(update, context):
    try:
        user_data_store["rate"] = float(update.message.text)
    except:
        update.message.reply_text("Enter valid number:")
        return RATE
    update.message.reply_text("CGST %:")
    return CGST

def cgst(update, context):
    try:
        user_data_store["cgst"] = float(update.message.text)
    except:
        update.message.reply_text("Enter valid number:")
        return CGST
    update.message.reply_text("SGST %:")
    return SGST

def sgst(update, context):
    try:
        user_data_store["sgst"] = float(update.message.text)
    except:
        update.message.reply_text("Enter valid number:")
        return SGST

    qty = user_data_store["qty"]
    rate = user_data_store["rate"]

    subtotal = qty * rate
    cgst_amt = subtotal * user_data_store["cgst"] / 100
    sgst_amt = subtotal * user_data_store["sgst"] / 100
    total = subtotal + cgst_amt + sgst_amt

    # COUNTER
    if not os.path.exists("invoice_counter.txt"):
        with open("invoice_counter.txt", "w") as f:
            f.write("0")

    with open("invoice_counter.txt", "r") as f:
        invoice_no = int(f.read()) + 1

    with open("invoice_counter.txt", "w") as f:
        f.write(str(invoice_no))

    file_name = f"invoice_{invoice_no}.pdf"

from reportlab.lib import colors

c = canvas.Canvas(file_name, pagesize=A4)

# ================= HEADER =================
c.setFont("Helvetica-Bold", 14)
c.drawString(50, 800, "STAR COOLING")

c.setFont("Helvetica", 10)
c.drawString(50, 785, "AC Repair & AMC Services")
c.drawString(50, 770, "Kolkata - 700033")
c.drawString(50, 755, "Mobile: +919007107975")
c.drawString(50, 740, "GSTIN: 19AAACS2838Z6")

# Right side info
c.drawString(400, 800, f"Invoice No: {invoice_no}")
c.drawString(400, 785, f"Date: {datetime.now().strftime('%d-%m-%Y')}")

# ================= BILL TO BOX =================
c.rect(50, 690, 500, 50)

c.setFont("Helvetica-Bold", 10)
c.drawString(55, 725, "Bill To:")

c.setFont("Helvetica", 10)
c.drawString(55, 710, user_data_store["name"])
c.drawString(55, 695, user_data_store["address"])

# ================= TABLE =================

# Column positions
x_desc = 55
x_qty = 300
x_rate = 360
x_amt = 440

y = 650

# Header row box
c.rect(50, y, 500, 25)

c.setFont("Helvetica-Bold", 10)
c.drawString(x_desc, y+8, "Description")
c.drawString(x_qty, y+8, "Qty")
c.drawString(x_rate, y+8, "Rate")
c.drawString(x_amt, y+8, "Amount")

# Item row
y -= 25
c.rect(50, y, 500, 25)

c.setFont("Helvetica", 10)
c.drawString(x_desc, y+8, user_data_store["item"])
c.drawString(x_qty, y+8, str(qty))
c.drawString(x_rate, y+8, f"{rate:.2f}")
c.drawString(x_amt, y+8, f"{subtotal:.2f}")

# ================= TOTALS =================

y -= 60

c.setFont("Helvetica", 10)
c.drawString(350, y, f"Subtotal: {subtotal:.2f}")
y -= 15
c.drawString(350, y, f"CGST ({user_data_store['cgst']}%): {cgst_amt:.2f}")
y -= 15
c.drawString(350, y, f"SGST ({user_data_store['sgst']}%): {sgst_amt:.2f}")

y -= 20
c.setFont("Helvetica-Bold", 11)
c.drawString(350, y, f"TOTAL: {total:.2f}")

# ================= SIGNATURE =================

signature_path = "signature.png"

if os.path.exists(signature_path):
    c.drawImage(
        signature_path,
        400, 500,
        width=120,
        height=60,
        preserveAspectRatio=True,
        mask='auto'
    )
else:
    c.drawString(400, 520, "No Signature Found")

c.setFont("Helvetica", 9)
c.drawString(400, 490, "Authorized Signatory")

# ================= FOOTER =================
c.setFont("Helvetica", 8)
c.drawString(50, 50, "This is a computer-generated invoice.")

c.save()

    update.message.reply_document(open(file_name, "rb"))

    return ConversationHandler.END


def cancel(update, context):
    update.message.reply_text("Cancelled")
    return ConversationHandler.END


conv = ConversationHandler(
    entry_points=[CommandHandler("newinvoice", start)],
    states={
        NAME: [MessageHandler(Filters.text, name)],
        ADDRESS: [MessageHandler(Filters.text, address)],
        ITEM: [MessageHandler(Filters.text, item)],
        QTY: [MessageHandler(Filters.text, qty)],
        RATE: [MessageHandler(Filters.text, rate)],
        CGST: [MessageHandler(Filters.text, cgst)],
        SGST: [MessageHandler(Filters.text, sgst)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

dispatcher.add_handler(conv)


# -------- WEBHOOK --------

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"


@app.route("/")
def home():
    return "Bot is running!"


# -------- MAIN --------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
