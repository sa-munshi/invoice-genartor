import os
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Updater, CommandHandler, MessageHandler,
    Filters, ConversationHandler, CallbackContext
)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# STATES
(NAME, ADDRESS, ITEM, QTY, RATE, CGST, SGST) = range(7)

user_data_store = {}

# ---------------- START ----------------

def start(update: Update, context: CallbackContext):
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

    # CALCULATION
    qty = user_data_store["qty"]
    rate = user_data_store["rate"]
    subtotal = qty * rate

    cgst_amt = subtotal * user_data_store["cgst"] / 100
    sgst_amt = subtotal * user_data_store["sgst"] / 100
    total = subtotal + cgst_amt + sgst_amt

    # INVOICE COUNTER (SAFE)
    if not os.path.exists("invoice_counter.txt"):
        with open("invoice_counter.txt", "w") as f:
            f.write("0")

    with open("invoice_counter.txt", "r") as f:
        invoice_no = int(f.read()) + 1

    with open("invoice_counter.txt", "w") as f:
        f.write(str(invoice_no))

    file_name = f"invoice_{invoice_no}.pdf"

    # PDF
    c = canvas.Canvas(file_name, pagesize=A4)

    # HEADER
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 800, "STAR COOLING")

    c.setFont("Helvetica", 10)
    c.drawString(50, 785, "AC Repair & AMC Services")
    c.drawString(50, 770, "Kolkata - 700033")
    c.drawString(50, 755, "Mobile: 9775500217")
    c.drawString(50, 740, "GSTIN: XXXXX")

    # INVOICE INFO
    c.drawString(400, 800, f"Invoice No: {invoice_no}")
    c.drawString(400, 785, f"Date: {datetime.now().strftime('%d-%m-%Y')}")

    # CUSTOMER
    c.drawString(50, 710, "Bill To:")
    c.drawString(50, 695, user_data_store["name"])
    c.drawString(50, 680, user_data_store["address"])

    # TABLE HEADER
    y = 640
    c.drawString(50, y, "Description")
    c.drawString(300, y, "Qty")
    c.drawString(350, y, "Rate")
    c.drawString(420, y, "Amount")

    # ITEM
    y -= 20
    c.drawString(50, y, user_data_store["item"])
    c.drawString(300, y, str(qty))
    c.drawString(350, y, str(rate))
    c.drawString(420, y, f"{subtotal:.2f}")

    # TOTALS
    y -= 40
    c.drawString(350, y, f"Subtotal: {subtotal:.2f}")
    y -= 15
    c.drawString(350, y, f"CGST ({user_data_store['cgst']}%): {cgst_amt:.2f}")
    y -= 15
    c.drawString(350, y, f"SGST ({user_data_store['sgst']}%): {sgst_amt:.2f}")
    y -= 15
    c.drawString(350, y, f"Total: {total:.2f}")

    # SIGNATURE
    if os.path.exists("signature.png"):
        c.drawImage("signature.png", 400, 500, width=120, height=50)

    c.drawString(400, 490, "Authorized Signatory")

    c.save()

    update.message.reply_document(open(file_name, "rb"))

    return ConversationHandler.END


def cancel(update, context):
    update.message.reply_text("Cancelled")
    return ConversationHandler.END


def main():
    TOKEN = os.getenv("BOT_TOKEN")

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

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

    dp.add_handler(conv)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
