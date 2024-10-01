import re
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Set up logging to track errors or debug
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Your Telegram bot token from BotFather
TOKEN = "7587534708:AAFTEWmTZBJG8RBMU5Fw_wOhci4H1BHdN6k"

# Function to validate credit card number using the Luhn Algorithm
def luhn_check(card_number):
    card_number = re.sub(r'\D', '', card_number)  # Remove all non-digit characters
    total = 0
    reverse_digits = card_number[::-1]  # Reverse the card number

    # Apply Luhn's Algorithm logic
    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:  # Double every second digit from the right
            n *= 2
            if n > 9:
                n -= 9  # Subtract 9 if doubling results in a number greater than 9
        total += n
    
    return total % 10 == 0  # Return true if total modulo 10 is 0 (valid)

# Function to process multiple cards and return their status
def process_cards(card_data):
    cards = card_data.splitlines()  # Split the input into lines (one card per line)
    results = []

    for card in cards:
        card = card.strip()  # Remove any leading/trailing spaces
        card_number = card.split('|')[0]  # Extract only the card number for validation
        if luhn_check(card_number):
            results.append(f"Live: {card}")
        else:
            results.append(f"Die: {card}")
    
    return "\n".join(results)

# Define the /start command to greet the user
def start(update, context):
    update.message.reply_text("Welcome to the Credit Card Checker Bot! Please send card details in the format card_number|expiry_month|expiry_year|cvv")

# Define the function that handles incoming messages (card numbers)
def handle_message(update, context):
    user_message = update.message.text
    try:
        # Process the card data using the process_cards function
        result = process_cards(user_message)
        update.message.reply_text(result)  # Send the validation result back to the user
    except Exception as e:
        update.message.reply_text(f"Error processing cards: {str(e)}")

def main():
    # Set up the Updater with your bot's token
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Define command and message handlers
    dp.add_handler(CommandHandler("start", start))  # Respond to /start command
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))  # Handle text messages (card data)

    # Start polling to listen for messages
    updater.start_polling()
    updater.idle()  # Run the bot until interrupted

if __name__ == '__main__':
    main()
