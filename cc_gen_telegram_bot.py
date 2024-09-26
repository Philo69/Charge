import telebot
import random
import sqlite3
import string

# Replace with your bot's token
TOKEN = '7587534708:AAHWUQf1PKBEqxRWZZ7XvJv2wEcNzUpxcgA'
OWNER_ID = 7202072688  # Replace with the actual Telegram user ID of the bot owner
bot = telebot.TeleBot(TOKEN)

# Connect to SQLite database (create the database and table if not exists)
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# Create users table if it doesn't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY, 
                    credits INTEGER DEFAULT 0, 
                    premium_status BOOLEAN DEFAULT FALSE,
                    is_registered BOOLEAN DEFAULT FALSE)''')

# Create redeem_codes table if it doesn't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS redeem_codes (
                    code TEXT PRIMARY KEY,
                    is_used BOOLEAN DEFAULT FALSE,
                    user_id INTEGER DEFAULT NULL)''')

# Create table to store card numbers for batch checking
cursor.execute('''CREATE TABLE IF NOT EXISTS card_numbers (
                    card_number TEXT PRIMARY KEY,
                    user_id INTEGER,
                    is_valid BOOLEAN DEFAULT FALSE)''')
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

# Function to generate a random valid credit card number using the Luhn algorithm
def luhn_checksum(card_number):
    def digits_of(n):
        return [int(d) for d in str(n)]
    
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10

def is_card_valid(card_number):
    return luhn_checksum(card_number) == 0

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

# Function to generate a random credit card number using a BIN
def generate_card_with_bin(bin_prefix, length=16):
    if len(bin_prefix) > length - 1:
        return None  # BIN too long for the card length
    
    number = [int(x) for x in bin_prefix]
    
    # Fill the card number with random digits
    while len(number) < (length - 1):
        number.append(random.randint(0, 9))
    
    # Calculate the check digit using the Luhn algorithm
    check_digit = luhn_checksum(int(''.join(map(str, number))) * 10)
    number.append((10 - check_digit) % 10)
    
    return ''.join(map(str, number))

# Command handler for /gencc to generate a card with a BIN
@bot.message_handler(commands=['gencc'])
def generate_card_number_with_bin(message):
    args = message.text.split()

    if len(args) != 2:
        bot.reply_to(message, "Please provide a valid BIN (6 digits). Example: /gencc 123456")
        return

    bin_input = args[1]

    if len(bin_input) != 6 or not bin_input.isdigit():
        bot.reply_to(message, "BIN should be exactly 6 digits.")
        return

    card_number = generate_card_with_bin(bin_input)

    if card_number:
        bot.reply_to(message, f"Generated card number: {card_number}")
    else:
        bot.reply_to(message, "There was an error generating the card number. Please check the BIN.")

# Command handler for /cmds to list all available commands
@bot.message_handler(commands=['cmds'])
def list_commands(message):
    commands = '''
    Available commands:
    /generate - Generate a random credit card number
    /redeem <code> - Redeem a premium code
    /credits - Check remaining credits
    /chk <card_number> - Check if the card number is authorized
    /mchk - Check all saved card numbers for authorization
    /luhn <card_number> - Check if the card number is valid according to the Luhn algorithm
    /gencc <BIN> - Generate a random card number based on a BIN (first 6 digits)
    /fake <country> - Generate a random fake address (Supported: USA, UK, Canada, Australia)
    /register - Register to the bot and receive 100 credits
    /generate_code <user_id> - (Owner only) Generate a redeem code for the user
    '''
    bot.reply_to(message, commands)

# Command handler for /register to allow users to register
@bot.message_handler(commands=['register'])
def register_user(message):
    user_id = message.from_user.id
    cursor.execute("SELECT is_registered FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if user and user[0]:
        bot.reply_to(message, "You are already registered!")
        return

    # Register user and give 100 credits
    cursor.execute("UPDATE users SET is_registered=?, credits=? WHERE user_id=?", (True, 100, user_id))
    conn.commit()
    bot.reply_to(message, "You have successfully registered and received 100 credits!")

# Function to ensure user is registered before executing any command
def ensure_registered(message):
    user_id = message.from_user.id
    cursor.execute("SELECT is_registered FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    return user and user[0]

# Other command handlers are the same as before, checking registration status
# You can reuse the other commands for generate, redeem, credits, etc.

# Start polling for Telegram messages
if __name__ == "__main__":
    bot.polling()
