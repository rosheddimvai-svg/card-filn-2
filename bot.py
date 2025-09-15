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
CARD_REVIEW_CHANNEL_ID = "-1003036699455" # Updated to the new channel ID
ADMIN_BROADCAST_CHANNEL_ID = "-1003018121134"
WITHDRAW_CHANNEL_ID = "-1002323042564"

# --- In-memory state for each user ---
user_states = {}
user_data = {}  # A simple dictionary to store user balances and withdrawal requests
submitted_cards = set() # A set to store submitted card details to prevent duplicates.
# NOTE: This data is in-memory and will be lost if the bot restarts.
# For a permanent solution, a database would be required.

# --- Card and Wallet format validation ---
CARD_FORMAT_REGEX = r'^\d{16}\|\d{2}\|\d{4}\|\d{3}$'

# --- ReplyKeyboardMarkup for persistent menu buttons (2x2 layout) ---
main_menu_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 My Balance"), KeyboardButton("💳 Card Sell")],
        [KeyboardButton("📜 Rules"), KeyboardButton("👨‍💻 Contact Admin")],
        [KeyboardButton("💸 Withdraw")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# --- Bot Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the main menu keyboard when the /start command is issued."""
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {"balance": 0}
    await update.message.reply_text(
        "Welcome! I am a bot for buying and selling Master/Visa cards. Please choose an option from the menu below:",
        reply_markup=main_menu_keyboard
    )

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button presses from the menu keyboard."""
    text = update.message.text
    user_id = update.effective_user.id

    if text == "💳 Card Sell":
        user_states[user_id] = "waiting_for_card"
        await update.message.reply_text(
            "Please send me your card details in the following format:\n\n`CARD_NUMBER|MM|YYYY|CVV`\n\nExample: `5598880391893502|07|2029|318`\n\nType 'cancel' to return."
        )
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
    elif text == "💰 My Balance":
        user_full_name = update.effective_user.full_name
        user_username = f"@{update.effective_user.username}" if update.effective_user.username else "N/A"
        balance = user_data.get(user_id, {}).get("balance", 0)

        message_text = (
            f"**💰 Your Balance Info**\n\n"
            f"**User:** {user_full_name} ({user_username})\n"
            f"**User ID:** `{user_id}`\n"
            f"**Current Balance:** **{balance} USDT**"
        )
        await update.message.reply_text(message_text, parse_mode="Markdown")
    elif text == "💸 Withdraw":
        if user_id not in user_data or user_data[user_id].get("balance", 0) <= 0:
            await update.message.reply_text("You have no balance to withdraw.")
            return

        user_states[user_id] = "waiting_for_withdraw_address"
        await update.message.reply_text("Please send the withdrawal address you would like to use.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming messages based on user's current state and admin's actions."""
    user_id = update.effective_user.id
    user_state = user_states.get(user_id, None)
    message = update.message
    
    # --- Handle regular user interactions based on state ---
    if user_state == "waiting_for_card":
        if message.photo:
            await message.reply_text("Please send the card details as a text message, not a photo. Photos are not accepted for verification.")
            return

        if message.text.lower() == "cancel":
            user_states.pop(user_id, None)
            await message.reply_text("Card submission cancelled.", reply_markup=main_menu_keyboard)
            return
        
        # Check for correct card format
        if not re.match(CARD_FORMAT_REGEX, message.text):
            await message.reply_text("The card details you sent are in the wrong format. Please send them again using the correct format.")
            return
            
        # Check if the card has already been submitted
        if message.text in submitted_cards:
            await message.reply_text("This card has already been submitted for review. You cannot submit it again.")
            return

        # Add the new card to the set of submitted cards
        submitted_cards.add(message.text)

        user_full_name = message.from_user.full_name
        user_mention = f"[{user_full_name}](tg://user?id={user_id})"
        user_username = f"@{message.from_user.username}" if message.from_user.username else "N/A"
        
        caption_text = (
            f"**💳 New Card Submission**\n\n"
            f"**User:** {user_mention} ({user_username})\n"
            f"**User ID:** `{user_id}`\n"
            f"**Card Details:**\n`{message.text}`"
        )
        
        review_keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{user_id}_{message.text}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
            ]]
        )
        
        # Added a try-except block here to handle potential errors when sending the message
        try:
            await context.bot.send_message(
                chat_id=CARD_REVIEW_CHANNEL_ID,
                text=caption_text,
                reply_markup=review_keyboard,
                parse_mode="Markdown"
            )
            # Updated confirmation message for the user
            await message.reply_text("আপনার কার্ড সাবমিট সম্পূর্ণ হয়েছে, আমরা শীঘ্রই এটি যাচাই করে আপনাকে জানাবো।")
            user_states.pop(user_id, None)
        except Exception as e:
            logger.error(f"Failed to send card submission to admin channel. Error: {e}", exc_info=True)
            await message.reply_text("Sorry, an error occurred while sending your card details for review. Please check if the bot is a member of the admin group with the correct permissions.")
        
    # --- Withdrawal handlers ---
    elif user_state == "waiting_for_withdraw_address":
        withdraw_address = message.text
        user_states[user_id] = {"state": "waiting_for_withdraw_amount", "withdraw_address": withdraw_address}
        await message.reply_text(f"Your withdrawal address is saved as:\n`{withdraw_address}`\n\nNow, please send the amount you want to withdraw.")

    elif isinstance(user_state, dict) and user_state.get("state") == "waiting_for_withdraw_amount":
        withdraw_address = user_state.get("withdraw_address")
        try:
            amount = float(message.text)
            current_balance = user_data.get(user_id, {}).get("balance", 0)
            
            if amount <= 0:
                await message.reply_text("Please enter a valid amount greater than zero.")
            elif amount > current_balance:
                await message.reply_text(f"You don't have enough balance. Your current balance is **{current_balance} USDT**.", parse_mode="Markdown")
            else:
                user_full_name = message.from_user.full_name
                user_mention = f"[{user_full_name}](tg://user?id={user_id})"
                
                withdraw_message = (
                    f"**💰 New Withdrawal Request**\n\n"
                    f"**User:** {user_mention}\n"
                    f"**User ID:** `{user_id}`\n"
                    f"**Amount:** **{amount} USDT**\n"
                    f"**Withdrawal Address:** `{withdraw_address}`"
                )
                
                withdraw_keyboard = InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton("✅ Approve", callback_data=f"withdraw_approve_{user_id}_{amount}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"withdraw_reject_{user_id}_{amount}")
                    ]]
                )
                
                try:
                    await context.bot.send_message(
                        chat_id=WITHDRAW_CHANNEL_ID,
                        text=withdraw_message,
                        reply_markup=withdraw_keyboard,
                        parse_mode="Markdown"
                    )
                    await message.reply_text(f"Withdrawal request for **{amount} USDT** has been sent. Your request is now pending approval.", parse_mode="Markdown")
                    user_states.pop(user_id, None)
                except Exception as e:
                    logger.error(f"Failed to send withdrawal request to admin channel. Error: {e}", exc_info=True)
                    await message.reply_text("Sorry, an error occurred while sending your withdrawal request. Please check if the bot is a member of the admin channel with the correct permissions.")

        except ValueError:
            await message.reply_text("Please enter a valid number for the withdrawal amount.")
        
    elif update.effective_user.id != ADMIN_USER_ID:
        user_mention = f"[{update.effective_user.full_name}](tg://user?id={user_id})"
        message_text = f"**New message from user:** {user_mention}\n" \
                       f"**User ID:** `{user_id}`\n" \
                       f"**Message:** {message.text}"
        
        await context.bot.send_message(
            chat_id=ADMIN_BROADCAST_CHANNEL_ID,
            text=message_text,
            parse_mode="Markdown"
        )
        await update.message.reply_text("Your message has been sent to the admin.")
    else:
        # A simple response for unhandled messages
        await update.message.reply_text("Sorry, I don't understand that command. Please use one of the menu buttons.")


# --- Admin Custom Balance Command Handler (Accessible only to Admin) ---
async def add_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /add_balance <user_id> <amount> command, accessible only by the ADMIN_USER_ID."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    try:
        if len(context.args) != 2:
            await update.message.reply_text("Usage: /add_balance <user_id> <amount>")
            return
        
        target_user_id = int(context.args[0])
        balance_amount = float(context.args[1])
        
        if target_user_id not in user_data:
            user_data[target_user_id] = {"balance": 0}
        
        user_data[target_user_id]["balance"] += balance_amount

        user_info = await context.bot.get_chat(target_user_id)
        user_full_name = user_info.full_name
        user_mention = f"[{user_full_name}](tg://user?id={target_user_id})"

        await update.message.reply_text(
            f"Balance of **{balance_amount} USDT** successfully added to {user_mention}'s account.", 
            parse_mode="Markdown"
        )
        
        # Send a confirmation message to the user
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"✅ **{balance_amount} USDT** has been added to your balance by the admin. Your new balance is **{user_data[target_user_id]['balance']} USDT**.",
            parse_mode="Markdown"
        )

    except (ValueError, IndexError):
        await update.message.reply_text("Invalid user ID or amount. Please check the format: /add_balance <user_id> <amount>")
    except Exception as e:
        logger.error(f"Error in add_balance_command: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred while adding the balance.")


# --- Admin Callback Handler ---
async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles admin's Confirm/Reject button presses for card reviews."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("You are not authorized to perform this action.")
        return

    data_parts = query.data.split('_', 2)
    action = data_parts[0]
    user_id = int(data_parts[1])
    card_details = data_parts[2] if len(data_parts) > 2 else "N/A"
    
    original_message_text = query.message.caption or query.message.text
    
    if action == "confirm":
        user_info = await context.bot.get_chat(user_id)
        user_full_name = user_info.full_name
        user_mention = f"[{user_full_name}](tg://user?id={user_id})"

        # Forward the original card submission to the public sales channel
        try:
            # Re-fetch the original message for forwarding
            original_message = await context.bot.get_message(
                chat_id=CARD_REVIEW_CHANNEL_ID,
                message_id=query.message.message_id
            )
            await original_message.forward(chat_id=ADMIN_BROADCAST_CHANNEL_ID)
            
            await query.edit_message_text(
                f"{original_message_text}\n\n**Status: ✅ APPROVED**\n\n**User:** {user_mention} \n**User ID:** `{user_id}`\n\nকার্ডটি বিক্রির জন্য দ্বিতীয় চ্যানেলে ফরোয়ার্ড করা হয়েছে।",
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Failed to forward message or edit confirmation. Error: {e}", exc_info=True)
            await query.edit_message_text(
                f"{original_message_text}\n\n**Status: ✅ APPROVED**\n\n**User:** {user_mention} \n**User ID:** `{user_id}`\n\nকার্ডটি অ্যাপ্রুভ করা হয়েছে, কিন্তু ফরোয়ার্ড করার সময় একটি সমস্যা হয়েছে।",
                parse_mode="Markdown"
            )
            
    elif action == "reject":
        try:
            # Send rejection message to the user
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ আপনার কার্ডটি বাতিল করা হয়েছে। অনুগ্রহ করে বিস্তারিত দেখে আবার চেষ্টা করুন।"
            )
            # Edit the original message in the review channel to show rejection status
            await query.edit_message_text(f"{original_message_text}\n\n**Status: ❌ REJECTED**\n\nএই কার্ডটি বাতিল করা হয়েছে।")

        except Exception as e:
            logger.error(f"Failed to handle reject action: {e}", exc_info=True)
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=f"Error handling reject action. Please check the bot logs. Error: {e}"
            )
    
async def handle_withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles admin's Withdraw Approve/Reject button presses."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("You are not authorized to perform this action.")
        return

    try:
        data_parts = query.data.split('_')
        action = data_parts[1]
        user_id = int(data_parts[2])
        amount = float(data_parts[3])

        user_info = await context.bot.get_chat(user_id)
        user_full_name = user_info.full_name
        user_mention = f"[{user_full_name}](tg://user?id={user_id})"
        
        if action == "approve":
            if user_data.get(user_id, {}).get("balance", 0) >= amount:
                user_data[user_id]["balance"] -= amount
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ Your withdrawal request for **{amount} USDT** has been successfully approved! Your new balance is **{user_data[user_id]['balance']} USDT**.",
                    parse_mode="Markdown"
                )
                await query.edit_message_text(
                    f"Withdrawal for {user_mention} has been **APPROVED**.\nAmount: **{amount} USDT**.\nUser's new balance: **{user_data[user_id]['balance']} USDT**",
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(f"Failed to approve withdrawal for {user_mention}. Insufficient balance.", parse_mode="Markdown")
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Your withdrawal request has been rejected due to insufficient balance.",
                    parse_mode="Markdown"
                )
        elif action == "reject":
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ Your withdrawal request for **{amount} USDT** has been rejected. Please contact the admin for more details.",
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                f"Withdrawal for {user_mention} has been **REJECTED**.\nAmount: **{amount} USDT**",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Error handling withdraw action: {e}", exc_info=True)
        await query.edit_message_text(f"An unexpected error occurred while processing the withdrawal request.")


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers for commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("add_balance", add_balance_command)) 

    # Handlers for messages
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & (~filters.Regex("^(💳 Card Sell|📜 Rules|👨‍💻 Contact Admin|💰 My Balance|💸 Withdraw)$")), handle_message))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & filters.Regex("^(💳 Card Sell|📜 Rules|👨‍💻 Contact Admin|💰 My Balance|💸 Withdraw)$"), handle_menu_selection))

    # Handlers for inline keyboard button presses
    application.add_handler(CallbackQueryHandler(handle_admin_action, pattern="^confirm_|^reject_"))
    application.add_handler(CallbackQueryHandler(handle_withdraw_action, pattern="^withdraw_approve_|^withdraw_reject_"))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
if __name__ == '__main__':
    main()
