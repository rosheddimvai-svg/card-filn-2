# This bot is designed for a public audience to sell Master/Visa cards.
# It uses ReplyKeyboardMarkup for persistent menu buttons.

import os
import re
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration (Your provided details) ---
BOT_TOKEN = "7845699149:AAEEKpzHFt5gd6LbApfXSsE8de64f8IaGx0"
ADMIN_USER_ID = int("7574558427")
CARD_REVIEW_CHANNEL_ID = "-1003036699455"
APPROVED_CARDS_CHANNEL_ID = "-1002944346537"
ADMIN_BROADCAST_CHANNEL_ID = "-1003018121134"

# --- In-memory state for each user ---
user_states = {}

# --- Card and Wallet format validation ---
CARD_FORMAT_REGEX = r'^\d{16}\|\d{2}\|\d{4}\|\d{3}$'
TRC20_WALLET_REGEX = r'^T[A-Za-z1-9]{33}$'

# --- ReplyKeyboardMarkup for persistent menu buttons (2x2 layout) ---
main_menu_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💳 Card Sell"), KeyboardButton("💰 Wallet Setup")],
        [KeyboardButton("📜 Rules"), KeyboardButton("👨‍💻 Contact Admin")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# --- Bot Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the main menu keyboard when the /start command is issued."""
    await update.message.reply_text(
        "Welcome! I am a bot for buying and selling Master/Visa cards. Please choose an option from the menu below:",
        reply_markup=main_menu_keyboard
    )

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button presses from the menu keyboard."""
    text = update.message.text
    
    if text == "💳 Card Sell":
        user_states[update.message.from_user.id] = "waiting_for_card"
        await update.message.reply_text(
            "Please send me your card details in the following format:\n\n`CARD_NUMBER|MM|YYYY|CVV`\n\nExample: `5598880391893502|07|2029|318`\n\nType 'cancel' to return."
        )
    elif text == "💰 Wallet Setup":
        user_states[update.message.from_user.id] = "waiting_for_wallet"
        await update.message.reply_text("Please send your TRC20 wallet address. This is where you will receive your payments.")
    elif text == "📜 Rules":
        await update.message.reply_text(
            "**Here are the rules for selling cards:**\n\n"
            "1. All cards must be valid.\n"
            "2. We are not responsible for invalid cards.\n"
            "3. The amount will be transferred to your provided wallet address after verification.\n\n"
            "For any queries, please contact @Rs_Rezaul_99."
        )
    elif text == "👨‍💻 Contact Admin":
        await update.message.reply_text("To contact an admin, please send your message. It will be forwarded. Or you can contact directly @Rs_Rezaul_99.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming messages based on user's current state and admin's actions."""
    user_id = update.effective_user.id
    user_state = user_states.get(user_id, None)
    message = update.message

    # Handle admin's balance input
    if user_id == ADMIN_USER_ID and user_state and "waiting_for_balance_input" in user_state:
        target_user_id = user_state["waiting_for_balance_input"]
        balance_info = message.text
        
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"✅ Good news! Your card has been successfully approved. Balance: `{balance_info}`. We will proceed with the payment."
        )
        await message.reply_text("Balance information sent to the user.")
        user_states.pop(user_id, None)
        return

    # Handle regular user interactions
    if user_state == "waiting_for_card":
        if message.photo:
            await message.reply_text("Please send the card details as a text message, not a photo. Photos are not accepted for verification.")
            return

        if message.text.lower() == "cancel":
            user_states.pop(user_id, None)
            await message.reply_text("Card submission cancelled.", reply_markup=main_menu_keyboard)
            return
        
        if not re.match(CARD_FORMAT_REGEX, message.text):
            await message.reply_text("The card details you sent are in the wrong format. Please send them again using the correct format.")
            return

        user_full_name = message.from_user.full_name
        user_username = f"@{message.from_user.username}" if message.from_user.username else "N/A"
        
        caption_text = (
            f"**💳 New Card Submission**\n\n"
            f"**User:** {user_full_name} ({user_username})\n"
            f"**User ID:** `{user_id}`\n\n"
            f"**Card Details:**\n`{message.text}`"
        )
        
        review_keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
            ]]
        )
        
        await context.bot.send_message(
            chat_id=CARD_REVIEW_CHANNEL_ID,
            text=caption_text,
            reply_markup=review_keyboard,
            parse_mode="Markdown"
        )
            
        await message.reply_text("Your card details have been sent for review. We will notify you of the result.")
        user_states.pop(user_id, None)

    elif user_state == "waiting_for_wallet":
        if not re.match(TRC20_WALLET_REGEX, message.text):
            await message.reply_text("The wallet address you sent is not a valid TRC20 address. Please send a valid one.")
            return

        await message.reply_text("Your TRC20 wallet address has been successfully saved!")
        user_states.pop(user_id, None)

    elif update.effective_user.id != ADMIN_USER_ID:
        user_mention = f"[{update.effective_user.full_name}](tg://user?id={update.effective_user.id})"
        message_text = f"**New message from user:** {user_mention}\n" \
                       f"**User ID:** `{user_id}`\n" \
                       f"**Message:** {message.text}"
        
        await context.bot.send_message(
            chat_id=ADMIN_BROADCAST_CHANNEL_ID,
            text=message_text,
            parse_mode="Markdown"
        )
        await update.message.reply_text("Your message has been sent to the admin.")

# --- Admin Callback Handler ---
async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles admin's Confirm/Reject button presses."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("You are not authorized to perform this action.")
        return

    action, user_id = query.data.split('_')
    user_id = int(user_id)
    
    original_message_text = query.message.caption or query.message.text
    
    if action == "confirm":
        user_states[query.from_user.id] = {"waiting_for_balance_input": user_id}
        await query.edit_message_text(f"{original_message_text}\n\n**Status: ✅ APPROVED**\n\nPlease reply to this message with the card balance.")
            
    elif action == "reject":
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Your card has been rejected. Please check the details and try again."
        )
        await query.edit_message_text(f"{original_message_text}\n\n**Status: ❌ REJECTED**")

# --- Broadcast Command for Admins ---
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Allows the admin to broadcast a message to a channel."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    
    message_text = " ".join(context.args)
    if not message_text:
        await update.message.reply_text("Please provide a message to broadcast. E.g., /broadcast Hello everyone!")
        return

    await context.bot.send_message(
        chat_id=ADMIN_BROADCAST_CHANNEL_ID,
        text=message_text,
    )
    await update.message.reply_text("Broadcast message sent successfully.")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_menu_selection))
    application.add_handler(CallbackQueryHandler(handle_admin_action, pattern="^confirm_|^reject_"))

    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
if __name__ == '__main__':
    main()
