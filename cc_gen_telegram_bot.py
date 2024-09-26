import telebot
import random
import sqlite3
import time
import requests
from datetime import datetime
from termcolor import colored

# Replace with your bot's token
TOKEN = '7587534708:AAFAL04YloAGcFzo7pXmXjPRj3WCeMZXuN0'
OWNER_ID = 7202072688  # Replace with your Telegram user ID as the bot owner/admin
bot = telebot.TeleBot(TOKEN)

# Connect to SQLite database (create the database and table if not exists)
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# Create users table if it doesn't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY, 
                    last_check_time INTEGER DEFAULT 0, 
                    premium_status BOOLEAN DEFAULT FALSE)''')
conn.commit()

# Fake address data for different countries (can be expanded)
fake_addresses = {
    'us': {
        'street_names': ['Maple Street', 'Oak Avenue', 'Pine Lane', 'Elm Road'],
        'cities': ['New York', 'Los Angeles', 'Chicago', 'Houston'],
        'postal_codes': ['10001', '90001', '60601', '77001']
    },
    'uk': {
        'street_names': ['High Street', 'Station Road', 'Main Street', 'Church Lane'],
        'cities': ['London', 'Manchester', 'Liverpool', 'Birmingham'],
        'postal_codes': ['EC1A', 'M1', 'L1', 'B1']
    }
}

# Function to validate Stripe secret key
def validate_stripe_key(sk_key):
    # Stripe secret key validation logic
    response = requests.get("https://api.stripe.com/v1/charges", auth=(sk_key, ''))
    if response.status_code == 200:
        return True
    else:
        return False

# Function to generate random credit cards based on BIN
def generate_credit_cards(bin_input, month=None, year=None):
    cards = []
    for _ in range(10):
        card_number = generate_card_with_bin(bin_input)
        exp_month = month if month else f"{random.randint(1, 12):02}"
        exp_year = year if year else f"{random.randint(23, 28)}"
        cvv = f"{random.randint(100, 999)}"
        cards.append(f"{card_number}|{exp_month}|{exp_year}|{cvv}")
    return cards

# Function to generate a random fake address based on country code
def generate_fake_address(country_code):
    if country_code not in fake_addresses:
        return None
    data = fake_addresses[country_code]
    street = random.choice(data['street_names'])
    city = random.choice(data['cities'])
    postal_code = random.choice(data['postal_codes'])
    house_number = random.randint(1, 9999)
    return f"{house_number} {street}, {city}, {postal_code}, {country_code.upper()}"

# Function to check rate limits for public users (30 seconds cooldown)
def is_user_limited(user_id):
    cursor.execute("SELECT last_check_time FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if user:
        last_check_time = user[0]
        current_time = time.time()
        return (current_time - last_check_time) < 30  # Check if it's within the 30-second limit
    return False

# Function to update last check time for user
def update_last_check_time(user_id):
    current_time = time.time()
    cursor.execute("UPDATE users SET last_check_time=? WHERE user_id=?", (current_time, user_id))
    conn.commit()

# Command handler to validate Stripe key
@bot.message_handler(commands=['sk'])
def check_stripe_key(message):
    sk_key = message.text.split(' ')[1]
    if validate_stripe_key(sk_key):
        bot.reply_to(message, "✅ Stripe key is valid!")
    else:
        bot.reply_to(message, "❌ Invalid Stripe key.")

# Command handler to generate credit cards based on BIN
@bot.message_handler(commands=['gen'])
def generate_bin_cards(message):
    args = message.text.split(' ')
    bin_input = args[1]
    month = args[2] if len(args) > 2 else None
    year = args[3] if len(args) > 3 else None
    cards = generate_credit_cards(bin_input, month, year)
    for card in cards:
        bot.reply_to(message, card)

# Command handler to generate a fake address based on country code
@bot.message_handler(commands=['fake'])
def fake_address(message):
    args = message.text.split(' ')
    country_code = args[1].lower()
    address = generate_fake_address(country_code)
    if address:
        bot.reply_to(message, f"Generated Address: {address}")
    else:
        bot.reply_to(message, "❌ Invalid country code.")

# Command handler to scrape CCs from a public channel or group
@bot.message_handler(commands=['scr'])
def scrape_ccs(message):
    args = message.text.split(' ')
    public_channel = args[1]
    amount = int(args[2])
    # Implement scraping logic here for the public_channel
    bot.reply_to(message, f"Scraped {amount} CCs from {public_channel} (fake data for demo)")

# Command handler for CC check (rate-limited for general users)
@bot.message_handler(commands=['cc'])
def check_credit_card(message):
    user_id = message.from_user.id
    if is_user_limited(user_id) and not is_user_premium(user_id):
        bot.reply_to(message, "❌ You can only check one CC every 30 seconds. Contact me for unlimited private access.")
    else:
        # CC check logic goes here (Stripe/VBV check)
        card_info = message.text.split(' ')[1]
        # For demo purposes, we'll assume the card is valid
        bot.reply_to(message, f"✅ Card {card_info} is valid (fake check for demo).")
        update_last_check_time(user_id)

# Check if a user is premium
def is_user_premium(user_id):
    cursor.execute("SELECT premium_status FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if user:
        return user[0]
    return False

# Command to grant premium access (for owner/admin only)
@bot.message_handler(commands=['grant_premium'])
def grant_premium(message):
    user_id = message.text.split(' ')[1]
    if message.from_user.id == OWNER_ID:
        cursor.execute("UPDATE users SET premium_status=? WHERE user_id=?", (True, user_id))
        conn.commit()
        bot.reply_to(message, f"✅ Granted premium access to user {user_id}.")
    else:
        bot.reply_to(message, "❌ You don't have permission to use this command.")

# Command handler for /cmds to list all available commands
@bot.message_handler(commands=['cmds'])
def list_commands(message):
    commands = '''
    ✅ /cc <card_info> - Check credit card information (Example: cc|month|year|cvv) - Stripe & VBV Check
    ✅ /sk <sk_key> - Validate Stripe secret key
    ✅ /gen <bin>|<month>|<year> - Generate 10 random credit cards
    ✅ /fake <country_code> - Generate random address (Example: fake us)
    ✅ /scr <public_channel> <amount> - Scrape CCs from public channels/groups
    ❌ General users can only check one CC every 30 seconds in public groups. Contact me for unlimited private access.
    '''
    bot.reply_to(message, commands)

# Start polling for Telegram messages
if __name__ == "__main__":
    bot.polling()
