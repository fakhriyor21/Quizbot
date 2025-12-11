import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from datetime import datetime
import json
import os

# Bot konfiguratsiyasi
API_TOKEN = '8470107212:AAGTgVUnxtN4xAr7tu_LhfWit0-JsOHi9Ns'
CHANNEL_ID = '@testlar231'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Ma'lumotlarni saqlash
TESTS_FILE = 'tests_db.json'
USERS_FILE = 'users_db.json'


def load_data():
    """Ma'lumotlarni fayldan yuklash"""
    global tests_db, user_results
    try:
        if os.path.exists(TESTS_FILE):
            with open(TESTS_FILE, 'r', encoding='utf-8') as f:
                tests_db = json.load(f)
        else:
            tests_db = {}

        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                user_results = json.load(f)
        else:
            user_results = {}
    except Exception as e:
        print(f"Ma'lumotlarni yuklashda xatolik: {e}")
        tests_db = {}
        user_results = {}


def save_data():
    """Ma'lumotlarni faylga saqlash"""
    try:
        with open(TESTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tests_db, f, ensure_ascii=False, indent=2)

        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_results, f, ensure_ascii=False, indent=2)
        print("Ma'lumotlar saqlandi")
    except Exception as e:
        print(f"Ma'lumotlarni saqlashda xatolik: {e}")


# Dastlabki ma'lumotlarni yuklash
load_data()

# Adminlar ro'yxati - o'zingizni ID ni qo'shing
ADMINS = [6777571934]  # O'z ID ni qo'shing


# Asosiy klaviatura
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("Mening natijalarim"),
        KeyboardButton("Testlar ro'yxati"),
        KeyboardButton("Test topshirish"),
        KeyboardButton("Yordam"),
        KeyboardButton("Reyting"),
        KeyboardButton("Admin panel")
    ]
    keyboard.add(*buttons)
    return keyboard


# Admin klaviatura
def admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("Test qo'shish"),
        KeyboardButton("Test o'chirish"),
        KeyboardButton("Barcha testlar"),
        KeyboardButton("Umumiy statistika"),
        KeyboardButton("Bosh menyu"),
        KeyboardButton("Foydalanuvchilar")
    ]
    keyboard.add(*buttons)
    return keyboard


# Start komandasi
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    welcome_text = "Assalomu alaykum! TestBotga xush kelibsiz!\n\n"
    welcome_text += "Bu bot orqali siz:\n"
    welcome_text += "• Turli testlarni yechishingiz mumkin\n"
    welcome_text += "• Natijalaringizni ko'rishingiz mumkin\n"
    welcome_text += "• Reytingda o'ringa ega bo'lishingiz mumkin\n\n"
    welcome_text += "Quyidagi tugmalardan foydalaning:"

    await message.answer(welcome_text, reply_markup=main_keyboard())

    # Foydalanuvchini qayd etish
    user_id = str(message.from_user.id)
    if user_id not in user_results:
        user_results[user_id] = {
            'username': message.from_user.username or message.from_user.full_name,
            'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'tests_taken': 0,
            'total_score': 0,
            'tests': {}
        }
        save_data()


# Testlar ro'yxati
@dp.message_handler(lambda message: message.text == "Testlar ro'yxati")
@dp.message_handler(commands=['tests'])
async def show_tests(message: types.Message):
    if not tests_db:
        await message.answer("Hozircha testlar mavjud emas! Kuting...")
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    for test_code in tests_db.keys():
        test = tests_db[test_code]
        questions_count = len(test['javoblar'])
        keyboard.add(InlineKeyboardButton(
            text=f"{test_code} ({questions_count} savol)",
            callback_data=f"test_info_{test_code}"
        ))

    keyboard.add(InlineKeyboardButton("Yangilash", callback_data="refresh_tests"))

    await message.answer("Mavjud testlar:\n\nQuyidagi testlardan birini tanlang:", reply_markup=keyboard)


# Test ma'lumotlari
@dp.callback_query_handler(lambda c: c.data.startswith('test_info_'))
async def test_info_callback(callback_query: types.CallbackQuery):
    test_code = callback_query.data.split('_')[2]

    if test_code not in tests_db:
        await callback_query.answer("Bu test mavjud emas!", show_alert=True)
        return

    test = tests_db[test_code]
    questions_count = len(test['javoblar'])

    info_text = f"Test: {test_code}\n\n"
    info_text += f"Ma'lumotlar:\n"
    info_text += f"• Savollar soni: {questions_count} ta\n"
    info_text += f"• Har bir to'g'ri javob: {test['narx']} ball\n"
    info_text += f"• Maksimal ball: {questions_count * test['narx']}\n\n"
    info_text += f"Testni topshirish uchun:\n`{test_code} ABCD...`\n"
    info_text += f"(javoblarni ketma-ket yozing)\n\n"
    info_text += f"Misol: `{test_code} {test['javoblar'][:5]}...`"

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Testni boshlash", callback_data=f"take_test_{test_code}"),
        InlineKeyboardButton("Statistika", callback_data=f"stats_{test_code}"),
        InlineKeyboardButton("Orqaga", callback_data="back_to_tests")
    )

    await callback_query.message.edit_text(info_text, parse_mode='Markdown', reply_markup=keyboard)
    await callback_query.answer()


# Test topshirish tugmasi
@dp.callback_query_handler(lambda c: c.data.startswith('take_test_'))
async def take_test_callback(callback_query: types.CallbackQuery):
    test_code = callback_query.data.split('_')[2]

    await callback_query.message.answer(
        f"{test_code} testini topshirish\n\n"
        f"Test kodini va javoblaringizni quyidagi formatda yuboring:\n\n"
        f"`{test_code} ABCDABCD...`\n\n"
        f"Eslatma: Javoblarni bir-biridan bo'sh joy qo'ymasdan yozing!\n"
        f"Misol: `{test_code} ABCDA`",
        parse_mode='Markdown'
    )
    await callback_query.answer()


# Mening natijalarim
@dp.message_handler(lambda message: message.text == "Mening natijalarim")
@dp.message_handler(commands=['mytests'])
async def my_results(message: types.Message):
    user_id = str(message.from_user.id)

    if user_id not in user_results or not user_results[user_id].get('tests'):
        await message.answer("Siz hali test topshirmagansiz!\n\n"
                             "Birinchi testni topshirish uchun:\n"
                             "1. 'Testlar ro'yxati' ni bosing\n"
                             "2. Testni tanlang\n"
                             "3. Test kodini va javoblaringizni yuboring\n\n"
                             "Yoki to'g'ridan-to'g'ri:\n`TEST123 ABCDA...`",
                             parse_mode='Markdown')
        return

    user_data = user_results[user_id]
    tests_data = user_data['tests']

    total_tests = len(tests_data)
    total_score = user_data.get('total_score', 0)
    avg_score = total_score / total_tests if total_tests > 0 else 0

    response = f"Sizning statistikangiz:\n\n"
    response += f"Umumiy:\n"
    response += f"• Testlar soni: {total_tests} ta\n"
    response += f"• Jami ball: {total_score}\n"
    response += f"• O'rtacha ball: {avg_score:.1f}\n\n"
    response += f"Testlar bo'yicha:\n"

    for test_code, results in tests_data.items():
        test_info = tests_db.get(test_code, {})
        total_q = len(test_info.get('javoblar', ''))
        max_score = total_q * test_info.get('narx', 0)

        response += f"\n{test_code}:\n"
        response += f"   To'g'ri: {results['correct']}/{total_q}\n"
        response += f"   Ball: {results['score']}/{max_score}\n"
        response += f"   Sana: {results.get('date', 'Noma\'lum')}\n"

    response += "\nStatistika:"

    # Inline tugmalar
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Natijalarni yuklash", callback_data="download_results"),
        InlineKeyboardButton("Tozalash", callback_data="clear_my_results")
    )

    await message.answer(response, reply_markup=keyboard)


# Testni tekshirish
@dp.message_handler(lambda message: len(message.text.split()) >= 2)
async def check_test(message: types.Message):
    try:
        parts = message.text.upper().split()
        if len(parts) < 2:
            return

        test_code = parts[0]
        user_answers = ''.join(parts[1:])

        if test_code not in tests_db:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("Testlar ro'yxatini ko'rish", callback_data="show_tests_list"))

            await message.answer(f"{test_code} testi topilmadi!\n\n"
                                 f"Ehtimol siz test kodini noto'g'ri kiritdingiz yoki bu test o'chirilgan.\n\n"
                                 f"To'g'ri test kodini kiriting yoki quyidagi tugma orqali mavjud testlarni ko'ring:",
                                 reply_markup=keyboard)
            return

        test = tests_db[test_code]
        correct_answers = test['javoblar']

        if len(user_answers) != len(correct_answers):
            await message.answer(f"Javoblar soni noto'g'ri!\n\n"
                                 f"Kutilgan: {len(correct_answers)} ta javob\n"
                                 f"Siz kiritdingiz: {len(user_answers)} ta\n\n"
                                 f"Savollar soni: {len(correct_answers)} ta\n"
                                 f"Har bir savol uchun: {test['narx']} ball\n\n"
                                 f"To'g'ri format: `{test_code} {'A' * len(correct_answers)}`",
                                 parse_mode='Markdown')
            return

        # Natijani hisoblash
        correct_count = sum(1 for i in range(len(correct_answers))
                            if user_answers[i] == correct_answers[i])
        wrong_count = len(correct_answers) - correct_count
        total_score = correct_count * test['narx']
        max_score = len(correct_answers) * test['narx']
        percentage = (correct_count / len(correct_answers)) * 100

        # Natijani baholash
        if percentage >= 90:
            grade = "A'lo!"
        elif percentage >= 80:
            grade = "Yaxshi!"
        elif percentage >= 60:
            grade = "Qoniqarli"
        else:
            grade = "Yana urinib ko'ring"

        # Natijani saqlash
        user_id = str(message.from_user.id)
        if user_id not in user_results:
            user_results[user_id] = {
                'username': message.from_user.username or message.from_user.full_name,
                'tests_taken': 0,
                'total_score': 0,
                'tests': {}
            }

        if test_code not in user_results[user_id]['tests']:
            user_results[user_id]['tests_taken'] += 1

        user_results[user_id]['tests'][test_code] = {
            'correct': correct_count,
            'wrong': wrong_count,
            'score': total_score,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'answers': user_answers
        }
        user_results[user_id]['total_score'] = user_results[user_id].get('total_score', 0) + total_score

        save_data()

        # Natijani chiqarish
        result_message = f"TEST NATIJALARI\n\n"
        result_message += f"Test: {test_code}\n"
        result_message += f"Umumiy savollar: {len(correct_answers)} ta\n\n"
        result_message += f"Sizning natijangiz:\n"
        result_message += f"To'g'ri javoblar: {correct_count} ta\n"
        result_message += f"Noto'g'ri javoblar: {wrong_count} ta\n"
        result_message += f"Olingan ball: {total_score}/{max_score}\n"
        result_message += f"Foiz: {percentage:.1f}%\n\n"
        result_message += f"Baholash: {grade}\n\n"
        result_message += f"Tafsilotlar:\n"

        # Har 5 ta savol uchun qisqacha natija
        for i in range(0, len(correct_answers), 5):
            chunk = ""
            for j in range(i, min(i + 5, len(correct_answers))):
                if user_answers[j] == correct_answers[j]:
                    chunk += f"{j + 1}+ "
                else:
                    chunk += f"{j + 1}- "
            result_message += chunk + "\n"

        # Inline keyboard
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("Batafsil natija", callback_data=f"detailed_{test_code}_{user_id}"),
            InlineKeyboardButton("Statistika", callback_data=f"user_stats_{user_id}"),
            InlineKeyboardButton("Yangi test", callback_data="take_another_test"),
            InlineKeyboardButton("Reyting", callback_data="show_rating")
        )

        await message.answer(result_message, reply_markup=keyboard)

    except Exception as e:
        await message.answer(f"Xatolik yuz berdi!\n\n"
                             f"Iltimos, quyidagi formatda yuboring:\n"
                             f"`TEST123 ABCDABCD...`\n\n"
                             f"To'g'ri misol: `MATH101 ABCDA`\n\n"
                             f"Agar muammo davom etsa, /help buyrug'idan foydalaning.",
                             parse_mode='Markdown')


# Admin panel
@dp.message_handler(lambda message: message.text == "Admin panel")
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.answer("Bu bo'lim faqat adminlar uchun!", reply_markup=main_keyboard())
        return

    admin_stats = f"Admin Panel\n\n"
    admin_stats += f"Statistika:\n"
    admin_stats += f"• Testlar soni: {len(tests_db)} ta\n"
    admin_stats += f"• Jami foydalanuvchilar: {len(user_results)} ta\n"
    admin_stats += f"• Test topshirganlar: {sum(1 for u in user_results.values() if u.get('tests_taken', 0) > 0)} ta\n\n"
    admin_stats += f"So'nggi testlar:\n"

    test_codes = list(tests_db.keys())[-5:]
    for code in test_codes:
        admin_stats += f"• {code} ({len(tests_db[code]['javoblar'])} savol)\n"

    await message.answer(admin_stats, reply_markup=admin_keyboard())


# Yangi test qo'shish
@dp.message_handler(lambda message: message.text == "Test qo'shish")
async def add_test_prompt(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    await message.answer("Yangi test qo'shish\n\n"
                         "Testni quyidagi formatda yuboring:\n\n"
                         "KOD: TEST123\n"
                         "SAVOLLAR: 5\n"
                         "JAVOBLAR: ABCDA\n"
                         "BALL: 2\n"
                         "1. Savol matni?\n"
                         "A) Birinchi variant\n"
                         "B) Ikkinchi variant\n"
                         "C) Uchinchi variant\n"
                         "D) To'rtinchi variant\n"
                         "2. Ikkinchi savol?\n"
                         "A) Variant A\n"
                         "B) Variant B\n"
                         "C) Variant C\n"
                         "D) Variant D\n\n"
                         "Eslatmalar:\n"
                         "• KOD faqat harf va raqamlardan iborat bo'lsin\n"
                         "• Javoblar faqat A,B,C,D harflarida\n"
                         "• Savollar raqam bilan boshlansin")


# Test qabul qilish
@dp.message_handler(lambda message: message.from_user.id in ADMINS and message.text and 'KOD:' in message.text)
async def process_new_test(message: types.Message):
    try:
        lines = message.text.strip().split('\n')

        # Ma'lumotlarni olish
        test_code = lines[0].split(':')[1].strip()
        questions_count = int(lines[1].split(':')[1].strip())
        answers = lines[2].split(':')[1].strip().upper()
        points = int(lines[3].split(':')[1].strip())

        # Savollarni qayta ishlash
        questions = []
        current_question = None

        for line in lines[4:]:
            line = line.strip()
            if not line:
                continue

            # Yangi savol
            if line[0].isdigit() and '.' in line:
                if current_question:
                    questions.append(current_question)
                current_question = {
                    'text': line,
                    'variants': []
                }
            # Variant
            elif line[0] in 'ABCD' and ')' in line:
                if current_question:
                    current_question['variants'].append(line)

        if current_question:
            questions.append(current_question)

        # Saqlash
        tests_db[test_code] = {
            'savollar': questions,
            'javoblar': answers,
            'narx': points,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'created_by': message.from_user.username or message.from_user.full_name
        }

        save_data()

        # Kanalga jo'natish
        test_post = f"YANGI TEST!\n\n"
        test_post += f"Test kodi: `{test_code}`\n"
        test_post += f"Savollar soni: {questions_count} ta\n"
        test_post += f"Har bir to'g'ri javob: {points} ball\n"
        test_post += f"Maksimal ball: {questions_count * points}\n\n"
        test_post += f"Testni topshirish:\n`{test_code} {answers}`\n\n"
        test_post += f"Muddati: Cheklanmagan\n"
        test_post += f"Ishonch darajasi: O'rta\n\n"
        test_post += f"Maslahat: Diqqat bilan o'qing va har bir savolga javob bering!"

        try:
            await bot.send_message(CHANNEL_ID, test_post, parse_mode='Markdown')
            await message.answer(f"Test muvaffaqiyatli qo'shildi!\n\nKanalga joylandi: {test_code}")
        except Exception as e:
            await message.answer(f"Test muvaffaqiyatli qo'shildi!\n\nKanalga joylashda xatolik: {e}")

    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}\n\nIltimos, formatni tekshiring!")


# Barcha testlar
@dp.message_handler(lambda message: message.text == "Barcha testlar")
async def all_tests_list(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    if not tests_db:
        await message.answer("Testlar mavjud emas")
        return

    response = "Barcha testlar:\n\n"

    for code, test in tests_db.items():
        response += f"{code}:\n"
        response += f"   Savollar: {len(test['javoblar'])} ta\n"
        response += f"   Ball: {test['narx']}/savol\n"
        response += f"   Yaratilgan: {test.get('created_at', 'Noma\'lum')}\n"
        response += f"   Muallif: {test.get('created_by', 'Noma\'lum')}\n\n"

    await message.answer(response)


# Reyting
@dp.message_handler(lambda message: message.text == "Reyting")
async def show_rating(message: types.Message):
    # Foydalanuvchilarni ballar bo'yicha saralash
    sorted_users = sorted(
        [(uid, data) for uid, data in user_results.items() if data.get('total_score', 0) > 0],
        key=lambda x: x[1].get('total_score', 0),
        reverse=True
    )[:10]  # Faqat top 10

    if not sorted_users:
        await message.answer("Hozircha reyting mavjud emas. Birinchi bo'ling!")
        return

    rating_text = "TOP 10 REYTING\n\n"

    for i, (user_id, user_data) in enumerate(sorted_users):
        username = user_data.get('username', 'Noma\'lum')
        total_score = user_data.get('total_score', 0)
        tests_taken = user_data.get('tests_taken', 0)

        rating_text += f"{i + 1}. {username}\n"
        rating_text += f"   Ball: {total_score}\n"
        rating_text += f"   Testlar: {tests_taken} ta\n"
        rating_text += f"   O'rtacha: {total_score / tests_taken:.1f} ball\n\n"

    rating_text += "\nO'z o'rningizni oshiring!"

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Yangilash", callback_data="refresh_rating"),
        InlineKeyboardButton("Umumiy statistika", callback_data="global_stats")
    )

    await message.answer(rating_text, reply_markup=keyboard)


# Yordam
@dp.message_handler(lambda message: message.text == "Yordam")
@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    help_text = "TEST BOT - YORDAM\n\n"
    help_text += "Test topshirish:\n"
    help_text += "1. Test kodini oling (kanaldan yoki ro'yxatdan)\n"
    help_text += "2. Botga yuboring: KOD JAVOBLAR\n"
    help_text += "   Masalan: MATH101 ABCDA\n\n"
    help_text += "Natijalarni ko'rish:\n"
    help_text += "• 'Mening natijalarim' tugmasi\n"
    help_text += "• Har bir testdan keyin avtomatik chiqadi\n\n"
    help_text += "Reyting:\n"
    help_text += "• 'Reyting' tugmasi bosish orqali\n"
    help_text += "• Eng yaxshi 10 ta foydalanuvchi\n\n"
    help_text += "Adminlar uchun:\n"
    help_text += "• Yangi test qo'shish\n"
    help_text += "• Testlarni boshqarish\n"
    help_text += "• Statistika ko'rish"

    await message.answer(help_text)


# Test o'chirish
@dp.message_handler(lambda message: message.text == "Test o'chirish")
async def delete_test_prompt(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    if not tests_db:
        await message.answer("Testlar mavjud emas")
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    for test_code in tests_db.keys():
        keyboard.add(InlineKeyboardButton(
            test_code,
            callback_data=f"delete_{test_code}"
        ))

    await message.answer("O'chirmoqchi bo'lgan testni tanlang:", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith('delete_'))
async def delete_test_callback(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMINS:
        await callback_query.answer("Ruxsat yo'q!", show_alert=True)
        return

    test_code = callback_query.data.split('_')[1]

    if test_code in tests_db:
        del tests_db[test_code]
        save_data()
        await callback_query.answer(f"{test_code} testi o'chirildi!", show_alert=True)
        await callback_query.message.edit_text(f"{test_code} testi muvaffaqiyatli o'chirildi!")
    else:
        await callback_query.answer("Test topilmadi!", show_alert=True)


# Callback query handler
@dp.callback_query_handler()
async def callback_handler(callback_query: types.CallbackQuery):
    data = callback_query.data

    if data == "refresh_tests":
        await show_tests(callback_query.message)

    elif data == "back_to_tests":
        await show_tests(callback_query.message)

    elif data == "take_another_test":
        await show_tests(callback_query.message)

    elif data == "show_tests_list":
        await show_tests(callback_query.message)

    elif data == "show_rating":
        await show_rating(callback_query.message)

    elif data == "refresh_rating":
        await callback_query.answer("Reyting yangilandi!")
        await show_rating(callback_query.message)

    elif data == "clear_my_results":
        user_id = str(callback_query.from_user.id)
        if user_id in user_results:
            user_results[user_id]['tests'] = {}
            user_results[user_id]['total_score'] = 0
            user_results[user_id]['tests_taken'] = 0
            save_data()
            await callback_query.answer("Natijalar tozalandi!", show_alert=True)
            await my_results(callback_query.message)

    elif data.startswith("detailed_"):
        parts = data.split('_')
        if len(parts) >= 3:
            test_code = parts[1]
            user_id = parts[2]

            if user_id in user_results and test_code in user_results[user_id]['tests']:
                results = user_results[user_id]['tests'][test_code]
                test_info = tests_db.get(test_code, {})
                correct_answers = test_info.get('javoblar', '')
                user_answers = results.get('answers', '')

                detailed = f"Batafsil natija - {test_code}:\n\n"
                for i in range(len(correct_answers)):
                    status = "+" if user_answers[i] == correct_answers[i] else "-"
                    detailed += f"{i + 1}. {status} Siz: {user_answers[i]}, To'g'ri: {correct_answers[i]}\n"

                await callback_query.message.answer(detailed)

    await callback_query.answer()


# Test topshirish menyusi
@dp.message_handler(lambda message: message.text == "Test topshirish")
async def take_test_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=2)

    for test_code in list(tests_db.keys())[:6]:  # Faqat 6 ta test
        test = tests_db[test_code]
        keyboard.add(InlineKeyboardButton(
            f"{test_code} ({len(test['javoblar'])} savol)",
            callback_data=f"take_test_{test_code}"
        ))

    keyboard.add(InlineKeyboardButton("Barcha testlar", callback_data="show_all_tests_for_taking"))

    await message.answer("Test topshirish\n\n"
                         "Quyidagi testlardan birini tanlang yoki to'g'ridan-to'g'ri test kodini kiriting:\n\n"
                         "KOD JAVOBLAR\n\n"
                         "Masalan: TEST123 ABCDA",
                         reply_markup=keyboard)


# Bosh menyu
@dp.message_handler(lambda message: message.text == "Bosh menyu")
async def main_menu(message: types.Message):
    await send_welcome(message)


# Foydalanuvchilar
@dp.message_handler(lambda message: message.text == "Foydalanuvchilar")
async def show_users(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    active_users = sum(1 for u in user_results.values() if u.get('tests_taken', 0) > 0)

    response = f"Foydalanuvchilar statistikasi:\n\n"
    response += f"Jami ro'yxatdan o'tganlar: {len(user_results)} ta\n"
    response += f"Faol foydalanuvchilar: {active_users} ta\n\n"
    response += f"So'nggi 5 ta foydalanuvchi:\n"

    # So'nggi 5 ta foydalanuvchi
    recent_users = list(user_results.items())[-5:]
    for user_id, user_data in recent_users:
        username = user_data.get('username', 'Noma\'lum')
        first_seen = user_data.get('first_seen', 'Noma\'lum')
        tests_taken = user_data.get('tests_taken', 0)

        response += f"• {username}\n"
        response += f"  ID: {user_id}\n"
        response += f"  Testlar: {tests_taken} ta\n"
        response += f"  Ro'yxatdan: {first_seen}\n\n"

    await message.answer(response)


# Umumiy statistika
@dp.message_handler(lambda message: message.text == "Umumiy statistika")
async def overall_stats(message: types.Message):
    if message.from_user.id not in ADMINS:
        return

    total_questions = sum(len(test['javoblar']) for test in tests_db.values())
    total_tests_taken = sum(user.get('tests_taken', 0) for user in user_results.values())
    total_score_given = sum(user.get('total_score', 0) for user in user_results.values())

    response = f"Umumiy statistika:\n\n"
    response += f"Testlar: {len(tests_db)} ta\n"
    response += f"Jami savollar: {total_questions} ta\n"
    response += f"Test topshirishlar: {total_tests_taken} ta\n"
    response += f"Berilgan ballar: {total_score_given} ball\n\n"

    if total_tests_taken > 0:
        avg_score_per_test = total_score_given / total_tests_taken
        response += f"O'rtacha ball/test: {avg_score_per_test:.1f}\n"

    # Eng mashhur testlar
    test_popularity = {}
    for user in user_results.values():
        for test_code in user.get('tests', {}):
            test_popularity[test_code] = test_popularity.get(test_code, 0) + 1

    if test_popularity:
        response += f"\nEng mashhur testlar:\n"
        sorted_tests = sorted(test_popularity.items(), key=lambda x: x[1], reverse=True)[:5]
        for test_code, count in sorted_tests:
            response += f"• {test_code}: {count} marta\n"

    await message.answer(response)


if __name__ == '__main__':
    print("TEST BOT ISHGA TUSHDI!")
    print("Funktsiyalar:")
    print("• Test tekshirish")
    print("• Natijalar statistikasi")
    print("• Reyting tizimi")
    print("• Admin panel")
    print("Ma'lumotlar faylga saqlanadi")

    executor.start_polling(dp, skip_updates=True)