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
WITHDRAW_CHANNEL_ID = "-1002323042564"

# --- In-memory state for each user ---
user_states = {}
user_data = {}  # A simple dictionary to store user balances and withdrawal requests

# --- Card and Wallet format validation ---
CARD_FORMAT_REGEX = r'^\d{16}\|\d{2}\|\d{4}\|\d{3}$'
BINANCE_PAY_ID_REGEX = r'^\d{8,16}$'

# --- ReplyKeyboardMarkup for persistent menu buttons (2x2 layout) ---
main_menu_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 My Balance"), KeyboardButton("💳 Card Sell")],
        [KeyboardButton("💰 Wallet Setup"), KeyboardButton("📜 Rules")],
        [KeyboardButton("💸 Withdraw"), KeyboardButton("👨‍💻 Contact Admin")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# --- Bot Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the main menu keyboard when the /start command is issued."""
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {"balance": 0, "binance_id": None}
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
    elif text == "💰 Wallet Setup":
        user_states[user_id] = "waiting_for_binance_id"
        await update.message.reply_text("Please send your Binance Pay ID (P-ID). This is where you will receive your payments.")
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
        binance_id = user_data.get(user_id, {}).get("binance_id", "Not set")

        message_text = (
            f"**💰 Your Balance & Wallet Info**\n\n"
            f"**User:** {user_full_name} ({user_username})\n"
            f"**User ID:** `{user_id}`\n"
            f"**Current Balance:** **{balance} USDT**\n"
            f"**Binance Pay ID:** `{binance_id}`"
        )
        await update.message.reply_text(message_text, parse_mode="Markdown")
    elif text == "💸 Withdraw":
        if user_id not in user_data or user_data[user_id].get("balance", 0) <= 0:
            await update.message.reply_text("You have no balance to withdraw.")
            return
        
        binance_id = user_data.get(user_id, {}).get("binance_id")
        if not binance_id:
            await update.message.reply_text("Please set up your Binance Pay ID first using the 'Wallet Setup' button.")
            return

        user_states[user_id] = "waiting_for_withdraw_amount"
        await update.message.reply_text(f"Your current balance is **{user_data[user_id]['balance']} USDT**. How much do you want to withdraw?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming messages based on user's current state and admin's actions."""
    user_id = update.effective_user.id
    user_state = user_states.get(user_id, None)
    message = update.message
    
    # Handle admin's balance input
    if user_id == ADMIN_USER_ID and isinstance(user_state, dict) and "waiting_for_custom_balance" in user_state:
        target_user_id = user_state["waiting_for_custom_balance"]
        balance_info = message.text
        
        try:
            balance_amount = float(balance_info)
            # Update user's balance
            current_balance = user_data.get(target_user_id, {}).get("balance", 0)
            if target_user_id not in user_data:
                user_data[target_user_id] = {"balance": 0, "binance_id": None}
            user_data[target_user_id]["balance"] += balance_amount
            
            user_info = await context.bot.get_chat(target_user_id)
            user_full_name = user_info.full_name
            user_mention = f"[{user_full_name}](tg://user?id={target_user_id})"
            
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"✅ Good news! Your card has been successfully approved. **{balance_amount} USDT** has been added to your balance. Your new balance is **{user_data[target_user_id]['balance']} USDT**.",
                parse_mode="Markdown"
            )
            await message.reply_text(f"Balance information for **{balance_amount} USDT** sent to {user_mention} and balance updated.", parse_mode="Markdown")
            user_states.pop(user_id, None)
        except ValueError:
            await message.reply_text("Invalid balance amount. Please enter a valid number.")
        return

    # Handle regular user interactions based on state
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
        user_mention = f"[{user_full_name}](tg://user?id={user_id})"
        user_username = f"@{message.from_user.username}" if message.from_user.username else "N/A"
        
        caption_text = (
            f"**💳 New Card Submission**\n\n"
            f"**User:** {user_mention} ({user_username})\n"
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

    elif user_state == "waiting_for_binance_id":
        if not re.match(BINANCE_PAY_ID_REGEX, message.text):
            await message.reply_text("The Binance Pay ID you sent is not valid. It must be a series of 8-16 digits. Please send a valid one.")
            return
        
        if user_id not in user_data:
            user_data[user_id] = {"balance": 0}
        user_data[user_id]["binance_id"] = message.text
        await message.reply_text("Your Binance Pay ID has been successfully saved! You can now use it to receive payments.")
        user_states.pop(user_id, None)
    
    elif user_state == "waiting_for_withdraw_amount":
        try:
            amount = float(message.text)
            current_balance = user_data.get(user_id, {}).get("balance", 0)
            
            if amount <= 0:
                await message.reply_text("Please enter a valid amount greater than zero.")
            elif amount > current_balance:
                await message.reply_text(f"You don't have enough balance. Your current balance is **{current_balance} USDT**.", parse_mode="Markdown")
            else:
                binance_id = user_data[user_id]["binance_id"]
                user_full_name = message.from_user.full_name
                user_mention = f"[{user_full_name}](tg://user?id={user_id})"
                
                withdraw_message = (
                    f"**💰 New Withdrawal Request**\n\n"
                    f"**User:** {user_mention}\n"
                    f"**User ID:** `{user_id}`\n"
                    f"**Amount:** **{amount} USDT**\n"
                    f"**Binance Pay ID:** `{binance_id}`"
                )
                
                withdraw_keyboard = InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton("✅ Approve", callback_data=f"withdraw_approve_{user_id}_{amount}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"withdraw_reject_{user_id}_{amount}")
                    ]]
                )

                await context.bot.send_message(
                    chat_id=WITHDRAW_CHANNEL_ID,
                    text=withdraw_message,
                    reply_markup=withdraw_keyboard,
                    parse_mode="Markdown"
                )
                
                await message.reply_text(f"Withdrawal request for **{amount} USDT** has been sent. Your request is now pending approval.", parse_mode="Markdown")
                user_states.pop(user_id, None)
        except ValueError:
            await message.reply_text("Please enter a valid number for the withdrawal amount.")

    elif update.effective_user.id != ADMIN_USER_ID and not isinstance(user_state, dict):
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
        # Forward the message to the approved channel
        await context.bot.copy_message(
            chat_id=APPROVED_CARDS_CHANNEL_ID,
            from_chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )

        user_info = await context.bot.get_chat(user_id)
        user_full_name = user_info.full_name
        user_mention = f"[{user_full_name}](tg://user?id={user_id})"

        balance_keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Add 5 USDT", callback_data=f"add_balance_{user_id}_5"),
                InlineKeyboardButton("Add 10 USDT", callback_data=f"add_balance_{user_id}_10"),
                InlineKeyboardButton("Add 20 USDT", callback_data=f"add_balance_{user_id}_20")
            ],
            [
                InlineKeyboardButton("Add 50 USDT", callback_data=f"add_balance_{user_id}_50"),
                InlineKeyboardButton("Custom Amount", callback_data=f"add_balance_custom_{user_id}")
            ]]
        )
        
        await query.edit_message_text(
            f"{original_message_text}\n\n**Status: ✅ APPROVED**\n\nChoose an amount to add to {user_mention}'s balance, or type a custom amount.",
            reply_markup=balance_keyboard,
            parse_mode="Markdown"
        )
            
    elif action == "reject":
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Your card has been rejected. Please check the details and try again."
        )
        await query.edit_message_text(f"{original_message_text}\n\n**Status: ❌ REJECTED**")

async def handle_add_balance_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles admin's preset balance buttons."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("You are not authorized to perform this action.")
        return

    data_parts = query.data.split('_')
    action = data_parts[0] + '_' + data_parts[1]
    
    if action == "add_balance":
        user_id = int(data_parts[2])
        amount_str = data_parts[3]

        if amount_str == "custom":
            user_states[query.from_user.id] = {"waiting_for_custom_balance": user_id}
            await query.edit_message_text(f"Please reply to this message with the exact amount to add to user `{user_id}`'s balance.")
            return

        amount = float(amount_str)
        if user_id not in user_data:
            user_data[user_id] = {"balance": 0, "binance_id": None}
        
        user_data[user_id]["balance"] += amount

        user_info = await context.bot.get_chat(user_id)
        user_full_name = user_info.full_name
        user_mention = f"[{user_full_name}](tg://user?id={user_id})"
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Good news! Your card has been successfully approved. **{amount} USDT** has been added to your balance. Your new balance is **{user_data[user_id]['balance']} USDT**.",
            parse_mode="Markdown"
        )
        await query.edit_message_text(
            f"Balance for {user_mention} has been updated.\nAmount: **{amount} USDT**.\nNew Balance: **{user_data[user_id]['balance']} USDT**",
            parse_mode="Markdown"
        )
    
async def handle_withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles admin's Withdraw Approve/Reject button presses."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("You are not authorized to perform this action.")
        return

    action, _, user_id_str, amount_str = query.data.split('_', 3)
    user_id = int(user_id_str)
    amount = float(amount_str)

    user_info = await context.bot.get_chat(user_id)
    user_full_name = user_info.full_name
    user_mention = f"[{user_full_name}](tg://user?id={user_id})"
    
    if action == "approve":
        # Check if the user has enough balance
        if user_data.get(user_id, {}).get("balance", 0) >= amount:
            user_data[user_id]["balance"] -= amount
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ Your withdrawal request for **{amount} USDT** has been successfully approved! Your new balance is **{user_data[user_id]['balance']} USDT**.",
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                f"Withdrawal for {user_mention} has been **APPROVED**.\nAmount: **{amount} USDT**",
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


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & (~filters.Regex("^(💳 Card Sell|💰 Wallet Setup|📜 Rules|👨‍💻 Contact Admin|💰 My Balance|💸 Withdraw)$")), handle_message))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & filters.Regex("^(💳 Card Sell|💰 Wallet Setup|📜 Rules|👨‍💻 Contact Admin|💰 My Balance|💸 Withdraw)$"), handle_menu_selection))
    application.add_handler(CallbackQueryHandler(handle_admin_action, pattern="^confirm_|^reject_"))
    application.add_handler(CallbackQueryHandler(handle_add_balance_action, pattern="^add_balance_"))
    application.add_handler(CallbackQueryHandler(handle_withdraw_action, pattern="^withdraw_approve_|^withdraw_reject_"))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
if __name__ == '__main__':
    main()
