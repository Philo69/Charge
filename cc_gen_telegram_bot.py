import telebot
import random
import sqlite3
import string

# Replace with your bot's token
TOKEN = '7587534708:AAHFg2Bhnj7DDUg5mX2s8cni3uWpl2aoogg'
OWNER_ID = 7587534708  # Replace with the actual Telegram user ID of the bot owner
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

def generate_card_number(prefix, length):
    number = [int(x) for x in str(prefix)]
    
    while len(number) < (length - 1):
        number.append(random.randint(0, 9))
    
    check_digit = luhn_checksum(int(''.join(map(str, number))) * 10)
    number.append((10 - check_digit) % 10)
    return ''.join(map(str, number))

# Function to validate if the card number is authorized using the Luhn algorithm
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

# Function to check if a user is registered
def is_user_registered(user_id):
    cursor.execute("SELECT is_registered FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    return user and user[0]  # Returns True if the user is registered

# Function to get or create a user
def get_or_create_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, credits, is_registered) VALUES (?, ?, ?)", (user_id, 0, False))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = cursor.fetchone()
    return user

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
    if not is_user_registered(user_id):
        bot.reply_to(message, "You need to register first by typing /register.")
        return False
    return True

# Command handler for /cmds to list all available commands
@bot.message_handler(commands=['cmds'])
def list_commands(message):
    if not ensure_registered(message):
        return
    commands = '''
    Available commands:
    /generate - Generate a random credit card number
    /redeem <code> - Redeem a premium code
    /credits - Check remaining credits
    /chk <card_number> - Check if the card number is authorized
    /mchk - Check all saved card numbers for authorization
    /fake <country> - Generate a random fake address (Supported: USA, UK, Canada, Australia)
    /register - Register to the bot and receive 100 credits
    /generate_code <user_id> - (Owner only) Generate a redeem code for the user
    '''
    bot.reply_to(message, commands)

# Command handler for /chk to check if a specific card is valid
@bot.message_handler(commands=['chk'])
def check_card(message):
    if not ensure_registered(message):
        return
    args = message.text.split()
    
    if len(args) != 2:
        bot.reply_to(message, "Please provide a card number. Example: /chk 1234567812345670")
        return
    
    card_number = args[1]
    
    if is_card_valid(card_number):
        bot.reply_to(message, f"Card {card_number} is valid!")
    else:
        bot.reply_to(message, f"Card {card_number} is invalid.")

# Command handler for /mchk to check all saved card numbers
@bot.message_handler(commands=['mchk'])
def batch_check_cards(message):
    if not ensure_registered(message):
        return
    cursor.execute("SELECT card_number FROM card_numbers")
    card_numbers = cursor.fetchall()
    
    if not card_numbers:
        bot.reply_to(message, "No card numbers saved for checking.")
        return
    
    valid_cards = []
    invalid_cards = []
    
    for (card_number,) in card_numbers:
        if is_card_valid(card_number):
            valid_cards.append(card_number)
        else:
            invalid_cards.append(card_number)
    
    response = "Batch card check results:\n"
    response += f"Valid cards: {', '.join(valid_cards)}\n" if valid_cards else "No valid cards.\n"
    response += f"Invalid cards: {', '.join(invalid_cards)}\n" if invalid_cards else "No invalid cards."
    
    bot.reply_to(message, response)

# Command handler for /fake <country> to generate a random fake address
@bot.message_handler(commands=['fake'])
def generate_fake_address_command(message):
    if not ensure_registered(message):
        return
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
    bot.reply_to(message, "Welcome to the CC Generator Bot! Type /cmds to see available commands. You must register first using /register to access the bot's features.")

# Command to redeem premium code
@bot.message_handler(commands=['redeem'])
def redeem_premium(message):
    if not ensure_registered(message):
        return
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
        cursor.execute("UPDATE redeem_codes SET is_used=?, user_id=? WHERE code=?", (True, user_id, code))
        conn.commit()
        bot.reply_to(message, "Congratulations! You have been upgraded to premium.")
    else:
        bot.reply_to(message, "Invalid or already used code. Please try again.")

# Command for owner to generate a redeem code for a user
@bot.message_handler(commands=['generate_code'])
def generate_code(message):
    if not ensure_registered(message):
        return
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        bot.reply_to(message, "You are not authorized to generate codes.")
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Please provide a user ID to generate a code for. Example: /generate_code 123456789")
        return
    
    target_user_id = int(args[1])

    # Generate a random redeem code
    redeem_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    
    # Store the redeem code in the database
    cursor.execute("INSERT INTO redeem_codes (code, user_id) VALUES (?, ?)", (redeem_code, target_user_id))
    conn.commit()
    
    bot.reply_to(message, f"Redeem code generated for user {target_user_id}: {redeem_code}")

# Command to generate a credit card number
@bot.message_handler(commands=['generate'])
def send_credit_card(message):
    if not ensure_registered(message):
        return
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    
    premium_status = user[2]  # premium_status is the third column
    credits = user[1]  # credits is the second column
    
    if premium_status:
        card_prefix = random.choice([4, 5])  # Visa starts with 4, MasterCard starts with 5
        card_number = generate_card_number(card_prefix, 16)
        bot.reply_to(message, f"Here is a random CC number: {card_number}")
        cursor.execute("INSERT INTO card_numbers (card_number, user_id, is_valid) VALUES (?, ?, ?)", 
                       (card_number, user_id, is_card_valid(card_number)))
        conn.commit()
    elif credits > 0:
        card_prefix = random.choice([4, 5])
        card_number = generate_card_number(card_prefix, 16)
        cursor.execute("UPDATE users SET credits=? WHERE user_id=?", (credits - 1, user_id))
        cursor.execute("INSERT INTO card_numbers (card_number, user_id, is_valid) VALUES (?, ?, ?)", 
                       (card_number, user_id, is_card_valid(card_number)))
        conn.commit()
        bot.reply_to(message, f"Here is a random CC number: {card_number}. You have {credits - 1} credits remaining.")
    else:
        bot.reply_to(message, "You have run out of credits. Please redeem a premium code or wait for more credits.")

# Command to check credit balance
@bot.message_handler(commands=['credits'])
def check_credits(message):
    if not ensure_registered(message):
        return
    user_id = message.from_user.id
    user = get_or_create_user(user_id)
    credits = user[1]
    premium_status = user[2]
    
    if premium_status:
        bot.reply_to(message, "You are a premium user with unlimited access!")
    else:
        bot.reply_to(message, f"You have {credits} credits remaining.")

# Start polling for Telegram messages
if __name__ == "__main__":
    bot.polling()
