from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from html import escape
import random
import math
from itertools import groupby
from shivu import collection, user_collection, application

# ✅ Rarity Mapping for Filtering
RARITY_MAP = {
    "Common": "🟢 Common",
    "Medium": "🔵 Medium",
    "Rare": "🟠 Rare",
    "Legendary": "🟡 Legendary",
    "Celestial": "🪽 Celestial",
    "Exclusive": "💮 Exclusive",
    "Special": "🎐 Special",
    "Premium": "💎 Premium",
    "Limited": "🔮 Limited",
    "Cosplay": "🔖 Cosplay"
}

ITEMS_PER_PAGE = 10

async def harem(update: Update, context: CallbackContext, page=0, edit=False):
    user_id = update.effective_user.id
    user = await user_collection.find_one({'id': user_id})
    
    if not user:
        return await update.message.reply_text("You need to register first by starting the bot in DM.")

    hmode = user.get('smode', 'default')
    characters = [c for c in user.get('characters', []) if isinstance(c, dict)]
    
    if hmode != 'default':
        rarity_value = RARITY_MAP.get(hmode)
        characters = [c for c in characters if c.get('rarity') == rarity_value]
    else:
        rarity_value = "All"

    if not characters:
        return await update.message.reply_text(f"You don't have any ({rarity_value}) characters. Change it with /smode.")

    # Sort and paginate
    characters.sort(key=lambda x: (x.get('anime', ''), x.get('id', '')))
    total_pages = math.ceil(len(characters) / ITEMS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))

    # Prepare message text
    header = f"<b>{escape(update.effective_user.first_name)}'s ({rarity_value}) Collection</b>\nPage {page + 1}/{total_pages}\n"
    message_text = header
    included = set()
    start, end = page * ITEMS_PER_PAGE, (page + 1) * ITEMS_PER_PAGE
    current_chars = characters[start:end]

    for anime, group in groupby(current_chars, key=lambda x: x['anime']):
        group_list = list(group)
        user_anime_count = sum(1 for c in characters if c.get('anime') == anime)
        total_anime_count = await collection.count_documents({"anime": anime})
        message_text += f"\n⌬ <b>{anime} [{user_anime_count}/{total_anime_count}]</b>\n"
        for c in group_list:
            if c['id'] not in included:
                count = sum(1 for x in characters if x['id'] == c['id'])
                message_text += f"ID: <b>{c['id']} ⌠ {c['rarity'][0]} ⌡ {c['name']} ×{count}</b>\n"
                included.add(c['id'])

    # Navigation buttons
    buttons = [[InlineKeyboardButton("🔍 View All", switch_inline_query_current_chat=f"collection.{user_id}")]]
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀ Prev", callback_data=f"harem:{page - 1}:{user_id}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶", callback_data=f"harem:{page + 1}:{user_id}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    reply_markup = InlineKeyboardMarkup(buttons)

    # Display image or text
    message = update.message or update.callback_query.message
    display_img = None

    # Use favorite image if available, else random
    fav_id = (user.get('favorites') or [None])[0]
    if fav_id:
        fav = next((c for c in characters if c['id'] == fav_id), None)
        display_img = fav.get('img_file_id') if fav else None
    if not display_img and characters:
        display_img = random.choice(characters).get('img_file_id')

    if edit:
        if display_img:
            await message.edit_media(
                media=InputMediaPhoto(media=display_img, caption=message_text, parse_mode='HTML'),
                reply_markup=reply_markup
            )
        else:
            await message.edit_caption(caption=message_text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        if display_img:
            await message.reply_photo(photo=display_img, caption=message_text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await message.reply_text(message_text, parse_mode='HTML', reply_markup=reply_markup)

# ✅ Callback Handler
async def harem_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    _, page, user_id = query.data.split(':')
    if int(user_id) != query.from_user.id:
        return await query.answer("It's not your harem!", show_alert=True)
    await query.answer()
    await harem(update, context, page=int(page), edit=True)

# ✅ Set Mode
async def set_hmode(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Default", callback_data="default"), InlineKeyboardButton("By Rarity", callback_data="rarity")]
    ]
    await update.message.reply_photo(
        photo="https://te.legra.ph/file/e714526fdc85b8800e1de.jpg",
        caption="Choose your harem sorting mode:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ✅ Rarity Selection
async def hmode_rarity(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton(r, callback_data=r) for r in list(RARITY_MAP.keys())[:3]],
        [InlineKeyboardButton(r, callback_data=r) for r in list(RARITY_MAP.keys())[3:6]],
        [InlineKeyboardButton(r, callback_data=r) for r in list(RARITY_MAP.keys())[6:9]],
        [InlineKeyboardButton(r, callback_data=r) for r in list(RARITY_MAP.keys())[9:]]
    ]
    await update.callback_query.edit_message_caption(
        caption="Choose rarity filter:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.callback_query.answer()

# ✅ Button Logic
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if data == "default":
        await user_collection.update_one({'id': user_id}, {'$set': {'smode': data}})
        await query.edit_message_caption("Sorting mode set to: Default")
    elif data == "rarity":
        await hmode_rarity(update, context)
    elif data in RARITY_MAP.keys():
        await user_collection.update_one({'id': user_id}, {'$set': {'smode': data}})
        await query.edit_message_caption(f"Sorting mode set to: {data}")
    await query.answer()

# ✅ Handlers
application.add_handler(CommandHandler(["myslave", "slaves"], harem))
application.add_handler(CallbackQueryHandler(harem_callback, pattern="^harem"))
application.add_handler(CommandHandler("smode", set_hmode))
application.add_handler(CallbackQueryHandler(button, pattern="^default$|^rarity$|" + "|".join(RARITY_MAP.keys())))
