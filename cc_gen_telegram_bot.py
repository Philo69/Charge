import telebot
import random
import sqlite3
import string

# Replace with your bot's token
TOKEN = 'your_bot_token_here'
OWNER_ID = 123456789  # Replace with the actual Telegram user ID of the bot owner
bot = telebot.TeleBot(TOKEN)

# Connect to SQLite database (create the database and table if not exists)
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# Create users table if it doesn't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY, 
                    credits INTEGER DEFAULT 10, 
                    premium_status BOOLEAN DEFAULT FALSE)''')

# Create redeem_codes table if it doesn't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS redeem_codes (
                    code TEXT PRIMARY KEY, 
                    is_used BOOLEAN DEFAULT FALSE,
                    used_by INTEGER)''')
conn.commit()

# Fake address data for different countries
fake_addresses = {
    'USA': {
        'street_names': ['Maple Street', 'Oak Avenue', 'Pine Lane', 'Elm Road'],
        'cities': ['New York', 'Los Angeles', 'Chicago', 'Houston'],
        'postal_codes': ['10001', '90001', '60601', '77001']
    },
    'UK': {
        'street_names': ['High Street', 'Station Road', 'Main Street', 'Church Lane'],
        'cities': ['London', 'Manchester', 'Liverpool', 'Birmingham'],
        'postal_codes': ['EC1A', 'M1', 'L1', 'B1']
    },
    'Canada': {
        'street_names': ['Queen Street', 'King Street', 'Dundas Street', 'Yonge Street'],
        'cities': ['Toronto', 'Vancouver', 'Montreal', 'Calgary'],
        'postal_codes': ['M5A', 'V6B', 'H2X', 'T2A']
    },
    'Australia': {
        'street_names': ['George Street', 'Pitt Street', 'Hunter Street', 'Kent Street'],
        'cities': ['Sydney', 'Melbourne', 'Brisbane', 'Perth'],
        'postal_codes': ['2000', '3000', '4000', '6000']
    }
}

# Function to generate a random fake address
def generate_fake_address(country):
    if country not in fake_addresses:
        return None
    
    country_data = fake_addresses[country]
    street = random.choice(country_data['street_names'])
    city = random.choice(country_data['cities'])
    postal_code = random.choice(country_data['postal_codes'])
    
    house_number = random.randint(1, 9999)
    address = f"{house_number} {street}, {city}, {postal_code}, {country}"
    
    return address

# Command handler for /fake <country>
@bot.message_handler(commands=['fake'])
def generate_fake_address_command(message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) != 2:
        bot.reply_to(message, "Please provide a country name. Example: /fake USA")
        return

    country = args[1].capitalize()

    # Generate a fake address for the requested country
    fake_address = generate_fake_address(country)

    if fake_address:
        bot.reply_to(message, f"Here is a fake address in {country}:\n{fake_address}")
    else:
        bot.reply_to(message, "Sorry, I don't have data for that country. Try USA, UK, Canada, or Australia.")

# Command handler for /start or /help
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to the CC Generator Bot! Type /generate to get a random CC number. "
                          "You have 10 free credits. Use /redeem <code> for premium features. "
                          "Type /fake <country> to generate a random fake address for that country.")

# Command to redeem premium code
@bot.message_handler(commands=['redeem'])
def redeem_premium(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) != 2:
        bot.reply_to(message, "Please provide a redeem code. Example: /redeem ABCD1234")
        return
    
    code = args[1]
    cursor.execute("SELECT * FROM redeem_codes WHERE code=? AND is_used=FALSE", (code,))
    redeem_code = cursor.fetchone()
    
    if redeem_code:
        cursor.execute("UPDATE users SET premium_status=? WHERE user_id=?", (True, user_id))
        cursor.execute("UPDATE redeem_codes SET is_used=?, used_by=? WHERE code=?", (True, user_id, code))
        conn.commit()
        bot.reply_to(message, "Congratulations! You have been upgraded to premium.")
    else:
        bot.reply_to(message, "Invalid or already used code. Please try again.")

# Command for owner to generate a redeem code
@bot.message_handler(commands=['generate_code'])
def generate_code(message):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        bot.reply_to(message, "You are not authorized to generate codes.")
        return
    
    redeem_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    cursor.execute("INSERT INTO redeem_codes (code) VALUES (?)", (redeem_code,))
    conn.commit()
    bot.reply_to(message, f"Redeem code generated: {redeem_code}")

# Command to generate a credit card number
@bot.message_handler(commands=['generate'])
def send_credit_card(message):
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    
    premium_status = user[2]  # premium_status is the third column
    credits = user[1]  # credits is the second column
    
    if premium_status:
        card_prefix = random.choice([4, 5])  # Visa starts with 4, MasterCard starts with 5
        card_number = generate_card_number(card_prefix, 16)
        bot.reply_to(message, f"Here is a random CC number: {card_number}")
    elif credits > 0:
        card_prefix = random.choice([4, 5])
        card_number = generate_card_number(card_prefix, 16)
        cursor.execute("UPDATE users SET credits=? WHERE user_id=?", (credits - 1, user_id))
        conn.commit()
        bot.reply_to(message, f"Here is a random CC number: {card_number}. You have {credits - 1} credits remaining.")
    else:
        bot.reply_to(message, "You have run out of credits. Please redeem a premium code or wait for more credits.")

# Command to check credit balance
@bot.message_handler(commands=['credits'])
def check_credits(message):
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    credits = user[1]
    premium_status = user[2]
    
    if premium_status:
        bot.reply_to(message, "You are a premium user with unlimited access!")
    else:
        bot.reply_to(message, f"You have {credits} credits remaining.")

# Start polling for Telegram messages
bot.polling()
  
