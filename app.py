import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, ConversationHandler
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from datetime import datetime

# ── STATES ──
(NAME, ADDRESS, PHONE, ITEM, QTY, RATE, CGST, SGST, CUSTOM_DATE, CUSTOM_BILLNO) = range(10)

user_data_store = {}

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

app = Flask(__name__)
dispatcher = Dispatcher(bot, None, use_context=True)

GSTIN = "19AAACS2838Z6"

# ── NUMBER TO WORDS ──
def num_to_words(n):
    n = int(n)
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def _below_1000(x):
        if x == 0: return ""
        elif x < 20: return ones[x]
        elif x < 100: return tens[x // 10] + (" " + ones[x % 10] if x % 10 else "")
        else: return ones[x // 100] + " Hundred" + (" " + _below_1000(x % 100) if x % 100 else "")

    if n == 0: return "Zero"
    parts = []
    if n >= 100000:
        parts.append(_below_1000(n // 100000) + " Lakh")
        n %= 100000
    if n >= 1000:
        parts.append(_below_1000(n // 1000) + " Thousand")
        n %= 1000
    if n > 0:
        parts.append(_below_1000(n))
    return " ".join(parts)


# ── PDF GENERATOR ──
def generate_pdf(data, file_name):
    c = canvas.Canvas(file_name, pagesize=A4)
    width, height = A4

    black      = colors.black
    dark       = colors.HexColor("#111111")
    light_gray = colors.HexColor("#f2f2f2")
    mid_gray   = colors.HexColor("#cccccc")

    # Outer border
    c.setStrokeColor(black)
    c.setLineWidth(1.5)
    c.rect(10*mm, 10*mm, width - 20*mm, height - 20*mm)

    # ── HEADER ──
    y = height - 18*mm
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width/2, y, "STAR COOLING")

    y -= 7*mm
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width/2, y, f"GSTIN: {GSTIN}")

    y -= 6*mm
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(width/2, y, "Mob: +91 9007107975")

    y -= 5*mm
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(width/2, y, "SPL. IN: ALL TYPES OF AC REPAIR & A.M.C. SERVICE | ALL TYPE SPARE PARTS AVAILABLE")

    y -= 5*mm
    c.drawCentredString(width/2, y, "House No. - 89, Tollygunje Road, Near Tollygunje, Bijoyee Sangha Club, Kol - 700033, W.B.")

    y -= 4*mm
    c.setStrokeColor(black)
    c.setLineWidth(1)
    c.line(10*mm, y, width - 10*mm, y)

    # ── TAX INVOICE BANNER ──
    y -= 9*mm
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width/2, y, "TAX INVOICE / GST BILL")

    y -= 4*mm
    c.setLineWidth(0.8)
    c.line(10*mm, y, width - 10*mm, y)

    # ── BILL META ──
    y -= 7*mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(13*mm, y, f"Bill No.: {data['invoice_no']}")
    y -= 5*mm
    c.drawString(13*mm, y, f"Date: {data['date']}")
    y -= 5*mm
    c.drawString(13*mm, y, "Place of Supply: West Bengal")

    y -= 4*mm
    c.setLineWidth(0.8)
    c.line(10*mm, y, width - 10*mm, y)

    # ── BILL TO BOX ──
    y -= 2*mm
    box_top = y
    box_h = 24*mm
    c.setStrokeColor(black)
    c.setLineWidth(0.8)
    c.rect(13*mm, box_top - box_h, width - 26*mm, box_h)

    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(16*mm, box_top - 6*mm, "BILL TO:")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(16*mm, box_top - 12*mm, data['name'])
    c.setFont("Helvetica", 8.5)
    c.drawString(16*mm, box_top - 17*mm, data['address'])
    if data.get('phone'):
        c.drawString(16*mm, box_top - 22*mm, f"Ph: {data['phone']}")

    # ── ITEMS TABLE ──
    left       = 13*mm
    right      = width - 13*mm
    col_sl_l   = left
    col_sl_r   = left + 12*mm
    col_desc_l = col_sl_r
    col_qty_l  = left + 115*mm
    col_qty_r  = left + 128*mm
    col_rate_l = col_qty_r
    col_rate_r = left + 153*mm
    col_amt_l  = col_rate_r
    col_amt_r  = right

    y = box_top - box_h - 6*mm
    hdr_h         = 8*mm
    body_h        = 14*mm
    table_top     = y
    table_total_h = hdr_h + body_h

    c.setStrokeColor(black)
    c.setLineWidth(0.8)
    c.rect(left, table_top - table_total_h, right - left, table_total_h)

    c.setFillColor(light_gray)
    c.rect(left, table_top - hdr_h, right - left, hdr_h, fill=1, stroke=0)

    c.setStrokeColor(black)
    for x in [col_sl_r, col_qty_l, col_qty_r, col_rate_r]:
        c.line(x, table_top, x, table_top - table_total_h)
    c.line(left, table_top - hdr_h, right, table_top - hdr_h)

    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString((col_sl_l + col_sl_r)/2,     table_top - 5.5*mm, "SL.")
    c.drawString(col_desc_l + 2*mm,                  table_top - 5.5*mm, "DESCRIPTION OF GOODS / SERVICE")
    c.drawCentredString((col_qty_l + col_qty_r)/2,   table_top - 5.5*mm, "QTY")
    c.drawCentredString((col_rate_l + col_rate_r)/2, table_top - 5.5*mm, "RATE (RS.)")
    c.drawCentredString((col_amt_l + col_amt_r)/2,   table_top - 5.5*mm, "AMOUNT (RS.)")

    qty_val  = data['qty']
    rate_val = data['rate']
    subtotal = qty_val * rate_val
    cgst_pct = data['cgst']
    sgst_pct = data['sgst']
    cgst_amt = subtotal * cgst_pct / 100
    sgst_amt = subtotal * sgst_pct / 100
    total    = subtotal + cgst_amt + sgst_amt

    qty_str  = str(int(qty_val)) if qty_val == int(qty_val) else f"{qty_val}"
    item_y   = table_top - hdr_h - 5*mm
    c.setFont("Helvetica", 9)
    c.drawCentredString((col_sl_l + col_sl_r)/2,     item_y, "1")
    c.drawString(col_desc_l + 2*mm,                  item_y, data['item'])
    c.drawCentredString((col_qty_l + col_qty_r)/2,   item_y, qty_str)
    c.drawRightString(col_rate_r - 2*mm,             item_y, f"{rate_val:,.2f}")
    c.drawRightString(col_amt_r - 3*mm,              item_y, f"{subtotal:,.2f}")

    # ── TOTALS ──
    y       = table_top - table_total_h - 6*mm
    label_x = 132*mm
    val_x   = col_amt_r - 3*mm

    def draw_total_row(label, value, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10 if bold else 9)
        c.drawRightString(label_x, y, label)
        c.drawRightString(val_x, y, value)
        y -= 6*mm

    draw_total_row("Sub Total:", f"Rs. {subtotal:,.2f}")
    draw_total_row(f"CGST @ {cgst_pct}%:", f"Rs. {cgst_amt:,.2f}")
    draw_total_row(f"SGST @ {sgst_pct}%:", f"Rs. {sgst_amt:,.2f}")

    c.setLineWidth(1)
    c.line(label_x - 28*mm, y + 4*mm, val_x, y + 4*mm)
    draw_total_row("TOTAL:", f"Rs. {total:,.2f}", bold=True)

    # ── AMOUNT IN WORDS ──
    y -= 3*mm
    c.setStrokeColor(mid_gray)
    c.setLineWidth(0.5)
    c.line(10*mm, y, width - 10*mm, y)
    y -= 6*mm
    words = num_to_words(round(total))
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(dark)
    c.drawString(13*mm, y, f"AMOUNT IN WORDS: {words.upper()} RUPEES ONLY")
    y -= 4*mm
    c.line(10*mm, y, width - 10*mm, y)

    # ── AUTHORISED SIGNATURE — bottom right ──
    sig_y = 20*mm
    sig_img = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signature.png")
    if os.path.exists(sig_img):
        c.drawImage(sig_img, width - 72*mm, sig_y + 1*mm, width=55*mm, height=18*mm, mask='auto')
    c.setStrokeColor(black)
    c.setLineWidth(0.8)
    c.line(width - 72*mm, sig_y, width - 13*mm, sig_y)
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(dark)
    c.drawCentredString(width - 42*mm, sig_y - 5*mm, "AUTHORISED SIGNATURE")

    c.save()


# ── HANDLERS ──

def start(update, context):
    uid = update.effective_user.id
    user_data_store[uid] = {}
    update.message.reply_text("🧾 *New Invoice*\n\nEnter customer name:", parse_mode="Markdown")
    return NAME

def get_name(update, context):
    uid = update.effective_user.id
    user_data_store[uid]["name"] = update.message.text.strip()
    update.message.reply_text("Enter customer address:")
    return ADDRESS

def get_address(update, context):
    uid = update.effective_user.id
    user_data_store[uid]["address"] = update.message.text.strip()
    update.message.reply_text("Enter customer phone number (or type `skip`):", parse_mode="Markdown")
    return PHONE

def get_phone(update, context):
    uid = update.effective_user.id
    val = update.message.text.strip()
    user_data_store[uid]["phone"] = "" if val.lower() == "skip" else val
    update.message.reply_text("Enter item description:")
    return ITEM

def get_item(update, context):
    uid = update.effective_user.id
    user_data_store[uid]["item"] = update.message.text.strip()
    update.message.reply_text("Enter quantity:")
    return QTY

def get_qty(update, context):
    uid = update.effective_user.id
    try:
        user_data_store[uid]["qty"] = float(update.message.text.strip())
    except:
        update.message.reply_text("❌ Invalid number. Enter quantity:")
        return QTY
    update.message.reply_text("Enter rate (price per unit):")
    return RATE

def get_rate(update, context):
    uid = update.effective_user.id
    try:
        user_data_store[uid]["rate"] = float(update.message.text.strip())
    except:
        update.message.reply_text("❌ Invalid number. Enter rate:")
        return RATE
    update.message.reply_text("Enter CGST % (e.g. 9):")
    return CGST

def get_cgst(update, context):
    uid = update.effective_user.id
    try:
        user_data_store[uid]["cgst"] = float(update.message.text.strip())
    except:
        update.message.reply_text("❌ Invalid. Enter CGST %:")
        return CGST
    update.message.reply_text("Enter SGST % (e.g. 9):")
    return SGST

def get_sgst(update, context):
    uid = update.effective_user.id
    try:
        user_data_store[uid]["sgst"] = float(update.message.text.strip())
    except:
        update.message.reply_text("❌ Invalid. Enter SGST %:")
        return SGST
    update.message.reply_text(
        "Enter date (DD-MM-YYYY) or type `today`:",
        parse_mode="Markdown"
    )
    return CUSTOM_DATE

def get_date(update, context):
    uid = update.effective_user.id
    val = update.message.text.strip()
    if val.lower() == "today":
        user_data_store[uid]["date"] = datetime.now().strftime("%d-%m-%Y")
    else:
        try:
            datetime.strptime(val, "%d-%m-%Y")
            user_data_store[uid]["date"] = val
        except:
            update.message.reply_text("❌ Use DD-MM-YYYY format or type `today`:")
            return CUSTOM_DATE
    update.message.reply_text(
        "Enter Bill No. or type `auto` for next auto number:",
        parse_mode="Markdown"
    )
    return CUSTOM_BILLNO

def get_billno(update, context):
    uid = update.effective_user.id
    val = update.message.text.strip()

    if val.lower() == "auto":
        counter_file = "invoice_counter.txt"
        if not os.path.exists(counter_file):
            with open(counter_file, "w") as f:
                f.write("0")
        with open(counter_file, "r") as f:
            invoice_no = int(f.read()) + 1
        with open(counter_file, "w") as f:
            f.write(str(invoice_no))
        user_data_store[uid]["invoice_no"] = str(invoice_no)
    else:
        user_data_store[uid]["invoice_no"] = val

    data = user_data_store[uid]
    file_name = f"invoice_{data['invoice_no']}.pdf"

    try:
        generate_pdf(data, file_name)
        update.message.reply_text(
            f"✅ Invoice *#{data['invoice_no']}* generated!\n"
            f"📅 Date: {data['date']}\n"
            f"👤 Customer: {data['name']}",
            parse_mode="Markdown"
        )
        with open(file_name, "rb") as f:
            update.message.reply_document(document=f, filename=file_name)
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)
        user_data_store.pop(uid, None)

    return ConversationHandler.END

def cancel(update, context):
    uid = update.effective_user.id
    user_data_store.pop(uid, None)
    update.message.reply_text("❌ Invoice cancelled.")
    return ConversationHandler.END

def help_cmd(update, context):
    update.message.reply_text(
        "📋 *Star Cooling Invoice Bot*\n\n"
        "Commands:\n"
        "/newinvoice — Start a new invoice\n"
        "/cancel — Cancel current invoice\n"
        "/help — Show this message",
        parse_mode="Markdown"
    )

conv = ConversationHandler(
    entry_points=[CommandHandler("newinvoice", start)],
    states={
        NAME:          [MessageHandler(Filters.text & ~Filters.command, get_name)],
        ADDRESS:       [MessageHandler(Filters.text & ~Filters.command, get_address)],
        PHONE:         [MessageHandler(Filters.text & ~Filters.command, get_phone)],
        ITEM:          [MessageHandler(Filters.text & ~Filters.command, get_item)],
        QTY:           [MessageHandler(Filters.text & ~Filters.command, get_qty)],
        RATE:          [MessageHandler(Filters.text & ~Filters.command, get_rate)],
        CGST:          [MessageHandler(Filters.text & ~Filters.command, get_cgst)],
        SGST:          [MessageHandler(Filters.text & ~Filters.command, get_sgst)],
        CUSTOM_DATE:   [MessageHandler(Filters.text & ~Filters.command, get_date)],
        CUSTOM_BILLNO: [MessageHandler(Filters.text & ~Filters.command, get_billno)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

dispatcher.add_handler(conv)
dispatcher.add_handler(CommandHandler("help", help_cmd))
dispatcher.add_handler(CommandHandler("start", help_cmd))

# ── WEBHOOK ──

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Star Cooling Invoice Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
