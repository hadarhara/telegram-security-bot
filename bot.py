import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
import requests
from PIL import Image
import io
import tempfile

# נייבא את ספריות ה-QR code
try:
    from pyzbar import pyzbar
    QR_AVAILABLE = True
    print("✅ pyzbar זמין - תמיכה ב-QR codes פעילה!")
except ImportError:
    QR_AVAILABLE = False
    print("⚠️ pyzbar לא מותקן - QR codes לא יעבדו")
    print("💡 להתקנה: pip install pyzbar")

# טוען את המשתנים מקובץ .env
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# הגדרת לוגים
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """פונקציה שמגיבה לפקודת /start"""
    user = update.effective_user
    qr_status = "✅ פעיל" if QR_AVAILABLE else "❌ לא זמין"
    
    welcome_message = f"""
🔒 שלום {user.first_name}!

אני בוט בדיקת אבטחה חכם 🤖

🎯 מה אני יכול לעשות:
• 🔗 בדיקת קישורים חשודים
• 📱 זיהוי QR codes ({qr_status})
• 🛡️ אמירה אם תוכן בטוח או לא

📝 איך להשתמש:
• שלח/י לי קישור לבדיקה
• שלח/י תמונה עם QR code

🆘 לעזרה: /help
📊 סטטיסטיקות: /stats
    """
    await update.message.reply_text(welcome_message)
    logger.info(f"User {user.id} started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """פונקציה שמגיבה לפקודת /help"""
    qr_help = """

📱 שליחת QR codes:
• שלח/י תמונה עם QR code
• אני אזהה את הקוד ואבדוק את התוכן
• אם יש קישור - אני אבדוק את הבטיחות שלו""" if QR_AVAILABLE else """

📱 QR codes:
❌ לא זמין כרגע (צריך התקנת ספריות)"""

    help_text = f"""
🆘 מדריך שימוש מפורט

📝 איך להשתמש בבוט:
1️⃣ שלח/י לי קישור כלשהו
2️⃣ או שלח/י תמונה עם QR code
3️⃣ אני אבדוק את התוכן אוטומטית
4️⃣ תקבל/י תשובה תוך שניות ספורות

🎯 פקודות זמינות:
/start - הודעת פתיחה
/help - המדריך הזה
/check <קישור> - בדיקה מפורשת
/stats - הסטטיסטיקות שלך
{qr_help}

⚠️ טיפי בטיחות:
• תמיד היה/י זהיר/ה עם קישורים ב-SMS
• QR codes יכולים להכיל קישורים מסוכנים
• אל תכניס/י פרטים אישיים באתרים חשודים
• אם משהו נראה חשוד - זה כנראה כן!

🔒 הבוט שומר על הפרטיות שלך ולא שומר תמונות או מידע אישי
    """
    await update.message.reply_text(help_text)

async def process_qr_code(image_bytes):
    """מעבד תמונה ומחפש QR codes"""
    if not QR_AVAILABLE:
        return {"success": False, "error": "pyzbar לא מותקן"}
    
    try:
        # פותח את התמונה עם Pillow
        image = Image.open(io.BytesIO(image_bytes))
        
        # מחפש QR codes בתמונה
        qr_codes = pyzbar.decode(image)
        
        if not qr_codes:
            return {"success": False, "error": "לא נמצא QR code בתמונה"}
        
        results = []
        for qr in qr_codes:
            # מחלץ את הטקסט מה-QR
            qr_data = qr.data.decode('utf-8')
            qr_type = qr.type
            
            results.append({
                "data": qr_data,
                "type": qr_type,
                "format": str(qr_type)
            })
        
        return {"success": True, "qr_codes": results}
        
    except Exception as e:
        return {"success": False, "error": f"שגיאה בעיבוד התמונה: {str(e)}"}

async def check_url_basic(url):
    """בדיקת URL בסיסית (נשדרג עם VirusTotal מאוחר יותר)"""
    # רשימת דומיינים בטוחים
    safe_domains = [
        'google.com', 'youtube.com', 'github.com', 'stackoverflow.com',
        'microsoft.com', 'apple.com', 'amazon.com', 'wikipedia.org'
    ]
    
    # רשימת מילות מפתח חשודות
    suspicious_words = [
        'free', 'win', 'prize', 'urgent', 'click', 'limited', 'offer',
        'bitcoin', 'crypto', 'money', 'bank', 'password', 'login'
    ]
    
    url_lower = url.lower()
    
    # בדיקה אם זה דומיין בטוח
    for domain in safe_domains:
        if domain in url_lower:
            return {
                "safe": True,
                "reason": f"דומיין בטוח מוכר: {domain}",
                "confidence": "גבוהה"
            }
    
    # בדיקה אחר מילות מפתח חשודות
    suspicious_found = []
    for word in suspicious_words:
        if word in url_lower:
            suspicious_found.append(word)
    
    if suspicious_found:
        return {
            "safe": False,
            "reason": f"נמצאו מילות מפתח חשודות: {', '.join(suspicious_found)}",
            "confidence": "בינונית"
        }
    
    # בדיקות נוספות
    if len(url) > 100:
        return {
            "safe": False,
            "reason": "URL ארוך חשוד מאוד",
            "confidence": "בינונית"
        }
    
    # אם לא נמצא כלום חשוד
    return {
        "safe": "unknown",
        "reason": "לא נמצא מידע חשוד, אבל היזהר",
        "confidence": "נמוכה"
    }

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """מטפל בתמונות שנשלחות לבוט"""
    user = update.effective_user
    
    if not QR_AVAILABLE:
        await update.message.reply_text(
            "❌ מצטער, זיהוי QR codes לא זמין כרגע\n"
            "💡 נדרשת התקנת ספריות נוספות"
        )
        return
    
    await update.message.reply_text("📱 קיבלתי תמונה! מחפש QR codes...")
    
    try:
        # מקבל את התמונה הכי איכותית
        photo = update.message.photo[-1]
        
        # מוריד את התמונה
        file = await context.bot.get_file(photo.file_id)
        
        # קורא את התמונה לזיכרון
        image_bytes = await file.download_as_bytearray()
        
        logger.info(f"User {user.id} sent photo for QR scanning")
        print(f"📸 עיבוד תמונה מ-{user.first_name}")
        
        # מעבד את ה-QR code
        qr_result = await process_qr_code(image_bytes)
        
        if not qr_result["success"]:
            await update.message.reply_text(f"❌ {qr_result['error']}")
            return
        
        # עובר על כל ה-QR codes שנמצאו
        for i, qr_info in enumerate(qr_result["qr_codes"]):
            qr_data = qr_info["data"]
            qr_type = qr_info["type"]
            
            response = f"✅ נמצא QR code #{i+1}:\n\n"
            response += f"📋 סוג: {qr_type}\n"
            response += f"💾 תוכן: {qr_data[:100]}{'...' if len(qr_data) > 100 else ''}\n\n"
            
            # אם זה URL - בודק אותו
            if qr_data.startswith(('http://', 'https://', 'www.')):
                response += "🔍 זיהיתי קישור! בודק בטיחות...\n\n"
                
                url_check = await check_url_basic(qr_data)
                
                if url_check["safe"] == True:
                    response += f"✅ הקישור נראה בטוח\n"
                    response += f"📊 סיבה: {url_check['reason']}\n"
                    response += f"🎯 רמת ביטחון: {url_check['confidence']}"
                elif url_check["safe"] == False:
                    response += f"⚠️ הקישור נראה חשוד!\n"
                    response += f"📊 סיבה: {url_check['reason']}\n"
                    response += f"🎯 רמת ביטחון: {url_check['confidence']}\n"
                    response += f"🚨 המלצה: אל תיכנס לקישור!"
                else:
                    response += f"🤔 לא בטוח לגבי הקישור\n"
                    response += f"📊 הערה: {url_check['reason']}\n"
                    response += f"⚠️ המלצה: התקדם בזהירות"
            
            elif '@' in qr_data:
                response += "📧 זה נראה כמו כתובת אימיל"
            elif qr_data.startswith('+') or qr_data.isdigit():
                response += "📞 זה נראה כמו מספר טלפון"
            else:
                response += "📝 זה טקסט רגיל"
            
            await update.message.reply_text(response)
        
        print(f"✅ סיום עיבוד QR עבור {user.first_name}")
        
    except Exception as e:
        error_msg = f"❌ שגיאה בעיבוד התמונה: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(f"Error processing photo: {e}")
        print(f"❌ שגיאה: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """מטפל בהודעות טקסט"""
    message_text = update.message.text
    user = update.effective_user
    
    # בודק אם יש קישור בהודעה
    if "http" in message_text.lower():
        await update.message.reply_text("🔍 זיהיתי קישור! בודק...")
        
        # מחלץ את הקישור הראשון
        words = message_text.split()
        url = None
        for word in words:
            if "http" in word.lower():
                url = word
                break
        
        if url:
            logger.info(f"User {user.id} sent URL: {url}")
            print(f"🔗 בודק קישור: {url}")
            
            # בודק את הקישור
            url_check = await check_url_basic(url)
            
            if url_check["safe"] == True:
                response = f"✅ הקישור נראה בטוח!\n\n"
                response += f"🔗 קישור: {url}\n"
                response += f"📊 סיבה: {url_check['reason']}\n"
                response += f"🎯 רמת ביטחון: {url_check['confidence']}"
            elif url_check["safe"] == False:
                response = f"⚠️ הקישור נראה חשוד!\n\n"
                response += f"🔗 קישור: {url}\n"
                response += f"📊 סיבה: {url_check['reason']}\n"
                response += f"🎯 רמת ביטחון: {url_check['confidence']}\n"
                response += f"🚨 המלצה: אל תיכנס לקישור!"
            else:
                response = f"🤔 לא בטוח לגבי הקישור\n\n"
                response += f"🔗 קישור: {url}\n"
                response += f"📊 הערה: {url_check['reason']}\n"
                response += f"⚠️ המלצה: התקדם בזהירות"
            
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("🤔 לא הצלחתי למצוא קישור תקין בהודעה")
    else:
        # הודעת ברירת מחדל
        qr_instruction = "\n📱 או שלח/י תמונה עם QR code" if QR_AVAILABLE else ""
        
        await update.message.reply_text(
            f"👋 שלום! אני בוט לבדיקת אבטחה\n\n"
            f"🔍 שלח/י לי קישור לבדיקה{qr_instruction}\n"
            f"🆘 או כתב/י /help לעזרה"
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """מציג סטטיסטיקות בסיסיות"""
    user = update.effective_user
    qr_status = "✅ פעיל" if QR_AVAILABLE else "❌ לא זמין (התקן: pip install pyzbar)"
    
    await update.message.reply_text(
        f"📊 הסטטיסטיקות שלך:\n\n"
        f"👤 שם: {user.first_name}\n"
        f"🆔 ID: {user.id}\n"
        f"🔍 בדיקת קישורים: ✅ פעיל\n"
        f"📱 זיהוי QR codes: {qr_status}\n\n"
        f"📈 סטטיסטיקות מתקדמות בקרוב!"
    )

def main():
    """פונקציית main - מפעילה את הבוט"""
    if not TOKEN:
        print("❌ שגיאה: לא נמצא טוקן!")
        print("💡 ודא/י שקובץ .env קיים ומכיל: BOT_TOKEN=הטוקן_שלך")
        return
    
    print("🤖 מפעיל את הבוט עם תמיכה ב-QR codes...")
    
    # יוצר את אפליקציית הבוט
    application = Application.builder().token(TOKEN).build()
    
    # מוסיף handlers לפקודות
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # מוסיף handler לתמונות (QR codes)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # מוסיף handler להודעות טקסט רגילות
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # מפעיל את הבוט
    print("✅ הבוט פועל עם תמיכה מלאה ב-QR codes!")
    print("📱 כעת אפשר לשלוח תמונות עם QR codes לבדיקה")
    print("🛑 לעצירה: Ctrl+C")
    application.run_polling()

if __name__ == '__main__':
    main()