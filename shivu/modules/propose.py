from pyrogram import filters
from shivu import shivuu as bot
from shivu import user_collection, collection
import asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
import random
import time

# Configurations
win_rate_percentage = 5  # Success chance in %
fight_fee = 20000  # Token fee for proposing
user_cooldowns = {}
user_last_command_times = {}

MUST_JOIN = 'https://t.me/+QJ7LM4ePd3NiNzNl'
OWNER_ID = 7598384653
ALLOWED_GROUP_ID = -1002097449198

# Messages & Images
start_messages = [
    "✨ Finally the time has come ✨",
    "💫 The moment you've been waiting for 💫",
    "🌟 The stars align for this proposal 🌟"
]
rejection_captions = [
    "She slapped you and ran away 😂",
    "She rejected you outright! 😂",
    "You got a harsh 'NO!' 😂"
]
acceptance_images = [
    "https://te.legra.ph/file/4fe133737bee4866a3549.png",
    "https://te.legra.ph/file/28d46e4656ee2c3e7dd8f.png",
    "https://te.legra.ph/file/d32c6328c6d271dd00816.png"
]
rejection_images = [
    "https://te.legra.ph/file/d6e784e5cda62ac27541f.png",
    "https://te.legra.ph/file/e4e1ba60b4e79359bf9e7.png",
    "https://te.legra.ph/file/81d011398da3a6f49fa7f.png"
]

# ----------------------
# Fetch Random Characters
# ----------------------
async def get_random_characters():
    target_rarities = ['🟡 Legendary', '🎐 Special']
    selected_rarity = random.choice(target_rarities)
    try:
        pipeline = [
            {'$match': {'rarity': selected_rarity}},
            {'$sample': {'size': 1}}
        ]
        cursor = collection.aggregate(pipeline)
        characters = await cursor.to_list(length=None)
        return characters
    except Exception as e:
        print("DB Error:", e)
        return []

# ----------------------
# Log Interaction
# ----------------------
async def log_interaction(user_id):
    group_id = ALLOWED_GROUP_ID
    await bot.send_message(group_id, f"User {user_id} used /propose at {time.strftime('%Y-%m-%d %H:%M:%S')}")

# ----------------------
# Reset Cooldown (Admin)
# ----------------------
@bot.on_message(filters.command("cd"))
async def reset_cooldown_command(_, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text("You don't have permission.")
    if not message.reply_to_message:
        return await message.reply_text("Reply to a user to reset cooldown.")
    target_user_id = message.reply_to_message.from_user.id
    user_cooldowns[target_user_id] = 0
    await message.reply_text(f"Cooldown reset for user {target_user_id}.")

# ----------------------
# Main Propose Command
# ----------------------
@bot.on_message(filters.command("propose"))
async def propose_command(_, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    current_time = time.time()

    # ✅ Check if user joined the required channel
    try:
        await bot.get_chat_member(MUST_JOIN, user_id)
    except UserNotParticipant:
        link = f"https://t.me/{MUST_JOIN}"
        return await message.reply_text(
            "You must join our channel to use this command.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join", url=link)]])
        )

    # ✅ Restrict to allowed group
    if chat_id != ALLOWED_GROUP_ID:
        return await message.reply_text("This command only works in @lustsupport")

    # ✅ Cooldown check (10 min)
    if user_id in user_cooldowns and current_time - user_cooldowns[user_id] < 600:
        remaining_time = 600 - (current_time - user_cooldowns[user_id])
        m, s = divmod(int(remaining_time), 60)
        return await message.reply_text(f"Cooldown active! Wait {m}:{s} minutes.")

    # ✅ Spam check (5 sec)
    if user_id in user_last_command_times and current_time - user_last_command_times[user_id] < 5:
        return await message.reply_text("You're too fast! Wait a few seconds.")
    user_last_command_times[user_id] = current_time

    # ✅ Check user balance
    user_data = await user_collection.find_one({'id': user_id}, {'balance': 1})
    user_balance = user_data.get('balance', 0) if user_data else 0
    if user_balance < fight_fee:
        return await message.reply_text("You need at least 200,000 tokens.")

    # ✅ Deduct tokens
    await user_collection.update_one({'id': user_id}, {'$inc': {'balance': -fight_fee}})

    # ✅ Apply cooldown
    user_cooldowns[user_id] = current_time

    # ✅ Start interaction
    await log_interaction(user_id)
    await bot.send_photo(chat_id, photo=random.choice(acceptance_images), caption=random.choice(start_messages))
    await asyncio.sleep(2)
    await message.reply_text(random.choice(["Proposing her... 💍", "Getting down on one knee... 💍", "Popping the question... 💍"]))
    await asyncio.sleep(2)

    # ✅ Success or fail
    if random.random() < (win_rate_percentage / 100):
        random_characters = await get_random_characters()
        if random_characters:
            for character in random_characters:
                await user_collection.update_one({'id': user_id}, {'$push': {'characters': character}})
                
                # ✅ Use img_file_id if available, fallback to img_url
                img = character.get('img_file_id') or character.get('img_url', '')
                caption = (
                    f"<b>{character['name']}</b> accepted your proposal! 😇\n"
                    f"Name: {character['name']}\n"
                    f"Rarity: {character['rarity']}\n"
                    f"Anime: {character['anime']}\n"
                )
                await message.reply_photo(photo=img, caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔥 View Harem", callback_data="view_harem")],
                        [InlineKeyboardButton("💍 Propose Again", callback_data="propose_again")]
                    ])
                )
    else:
        await message.reply_photo(
            photo=random.choice(rejection_images),
            caption=random.choice(rejection_captions),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💍 Try Again", callback_data="propose_again")]
            ])
        )
