"""
╔══════════════════════════════════════════╗
║      DATABASE HANDLER — MongoDB Async    ║
║   Motor (async) driver — No SQLite!      ║
╚══════════════════════════════════════════╝

Collections:
  posts, buttons, reactions, reaction_counts,
  sent_messages, user_settings, user_channels,
  channel_projects, channel_post_reactions,
  channel_post_user_reactions, counters
"""

import os
import logging
from datetime import datetime, timezone, timedelta

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, ReturnDocument

logger = logging.getLogger(__name__)

# ── Connection ──────────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://buttonbot:aaghaz9431@buttonbot.x2bdflb.mongodb.net/?appName=buttonbot"
)
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "button_bot")

_client: AsyncIOMotorClient | None = None
_database = None


def _db():
    global _client, _database
    if _database is None:
        _client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        _database = _client[MONGO_DB_NAME]
    return _database


# ── Collection accessors ───────────────────────────────────────────────────────
def _posts():        return _db()["posts"]
def _btns():         return _db()["buttons"]
def _rxns():         return _db()["reactions"]          # per-user reaction log
def _rxc():          return _db()["reaction_counts"]    # aggregate counts per post
def _sent():         return _db()["sent_messages"]
def _sett():         return _db()["user_settings"]
def _uchans():       return _db()["user_channels"]
def _proj():         return _db()["channel_projects"]
def _chreact():      return _db()["channel_post_reactions"]
def _chureact():     return _db()["channel_post_user_reactions"]
def _ctr():          return _db()["counters"]
def _users():        return _db()["users"]              # all registered users


# ── Auto-increment integer IDs ─────────────────────────────────────────────────
async def _next_id(name: str) -> int:
    """Atomic auto-increment counter. Returns next integer ID."""
    doc = await _ctr().find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["seq"]


# ── Dict helper: add 'id' alias for '_id' ─────────────────────────────────────
def _row(doc: dict | None) -> dict | None:
    """Adds 'id' key equal to '_id' so bot.py code works unchanged."""
    if doc is None:
        return None
    doc["id"] = doc["_id"]
    return doc


def _rows(docs: list[dict]) -> list[dict]:
    return [_row(d) for d in docs]


# ══════════════════════════════════════════════════════════
#   INITIALIZATION
# ══════════════════════════════════════════════════════════

async def init_db():
    """Create all necessary MongoDB indexes."""
    await _users().create_index([("user_id", ASCENDING)], unique=True)
    await _users().create_index([("joined_at", ASCENDING)])

    await _posts().create_index([("user_id", ASCENDING)])
    await _posts().create_index([("created_at", ASCENDING)])

    await _btns().create_index([("post_id", ASCENDING)])
    await _btns().create_index([
        ("post_id", ASCENDING), ("row_num", ASCENDING), ("order_num", ASCENDING)
    ])

    await _rxns().create_index(
        [("post_id", ASCENDING), ("user_id", ASCENDING)], unique=True
    )

    await _sent().create_index([("post_id", ASCENDING)])

    await _uchans().create_index([("user_id", ASCENDING)])
    await _uchans().create_index(
        [("user_id", ASCENDING), ("channel_username_or_id", ASCENDING)], unique=True
    )

    await _proj().create_index([("user_id", ASCENDING)])
    await _proj().create_index([("channel_id", ASCENDING)], unique=True)

    await _chreact().create_index(
        [("channel_id", ASCENDING), ("message_id", ASCENDING)], unique=True
    )
    await _chureact().create_index(
        [("channel_id", ASCENDING), ("message_id", ASCENDING), ("user_id", ASCENDING)],
        unique=True
    )

    logger.info("database: ✅ MongoDB connected and indexes ensured.")


# ══════════════════════════════════════════════════════════
#   USER REGISTRATION
# ══════════════════════════════════════════════════════════

async def register_user(user_id: int, username: str = None,
                        first_name: str = None, last_name: str = None) -> bool:
    """
    Register (or update) a user on /start.
    Returns True if this is a NEW user, False if already registered.
    """
    now = datetime.now(timezone.utc)
    try:
        result = await _users().update_one(
            {"user_id": user_id},
            {
                "$setOnInsert": {"joined_at": now},
                "$set": {
                    "username":   username,
                    "first_name": first_name,
                    "last_name":  last_name,
                    "last_seen":  now,
                },
            },
            upsert=True,
        )
        return result.upserted_id is not None   # True = new user
    except Exception:
        return False


async def count_total_users() -> int:
    return await _users().count_documents({})


async def count_today_users() -> int:
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return await _users().count_documents({"joined_at": {"$gte": today_start}})



# ══════════════════════════════════════════════════════════
#   POST OPERATIONS
# ══════════════════════════════════════════════════════════

async def create_post(user_id: int, content_type: str, content: str,
                      caption: str = None) -> int:
    """Create a new post. Returns integer post_id."""
    post_id = await _next_id("posts")
    now = datetime.now(timezone.utc)
    await _posts().insert_one({
        "_id":          post_id,
        "user_id":      user_id,
        "content_type": content_type,
        "content":      content,
        "caption":      caption,
        "parse_mode":   "HTML",
        "created_at":   now,
        "updated_at":   now,
    })
    # Create empty reaction counts row
    await _rxc().update_one(
        {"_id": post_id},
        {"$setOnInsert": {"likes": 0, "dislikes": 0, "views": 0, "shares": 0}},
        upsert=True,
    )
    return post_id


async def get_post(post_id: int) -> dict | None:
    doc = await _posts().find_one({"_id": post_id})
    return _row(doc)


async def get_user_posts(user_id: int, limit: int = 50) -> list[dict]:
    cursor = _posts().find({"user_id": user_id}).sort("created_at", DESCENDING).limit(limit)
    docs = await cursor.to_list(length=limit)
    # Attach reaction counts
    result = []
    for doc in docs:
        rc = await _rxc().find_one({"_id": doc["_id"]}) or {}
        doc["likes"]    = rc.get("likes", 0)
        doc["dislikes"] = rc.get("dislikes", 0)
        doc["views"]    = rc.get("views", 0)
        result.append(_row(doc))
    return result


async def count_user_posts(user_id: int) -> int:
    return await _posts().count_documents({"user_id": user_id})


async def delete_post(post_id: int, user_id: int) -> bool:
    result = await _posts().delete_one({"_id": post_id, "user_id": user_id})
    if result.deleted_count > 0:
        # Cascade delete
        await _btns().delete_many({"post_id": post_id})
        await _rxns().delete_many({"post_id": post_id})
        await _rxc().delete_one({"_id": post_id})
        await _sent().delete_many({"post_id": post_id})
        return True
    return False


async def delete_all_user_posts(user_id: int) -> int:
    """Deletes all posts for a user and returns the count of deleted posts."""
    # Find all post IDs for this user
    cursor = _posts().find({"user_id": user_id}, {"_id": 1})
    post_ids = [doc["_id"] async for doc in cursor]
    
    if not post_ids:
        return 0

    # Delete all posts
    result = await _posts().delete_many({"user_id": user_id})
    
    # Cascade delete for all post IDs
    await _btns().delete_many({"post_id": {"$in": post_ids}})
    await _rxns().delete_many({"post_id": {"$in": post_ids}})
    await _rxc().delete_many({"_id": {"$in": post_ids}})
    await _sent().delete_many({"post_id": {"$in": post_ids}})
    
    return result.deleted_count


async def update_post_content(post_id: int, content: str, caption: str = None):
    await _posts().update_one(
        {"_id": post_id},
        {"$set": {"content": content, "caption": caption,
                  "updated_at": datetime.now(timezone.utc)}}
    )


# ══════════════════════════════════════════════════════════
#   BUTTON OPERATIONS
# ══════════════════════════════════════════════════════════

async def add_button(post_id: int, button_type: str, text: str,
                     url: str = None, callback_data: str = None,
                     color: str = "default",
                     row_num: int = 0, order_num: int = 0) -> int:
    btn_id = await _next_id("buttons")
    await _btns().insert_one({
        "_id":           btn_id,
        "post_id":       post_id,
        "button_type":   button_type,
        "text":          text,
        "url":           url,
        "callback_data": callback_data,
        "color":         color,
        "row_num":       row_num,
        "order_num":     order_num,
    })
    return btn_id


async def get_post_buttons(post_id: int) -> list[dict]:
    cursor = _btns().find({"post_id": post_id}).sort(
        [("row_num", ASCENDING), ("order_num", ASCENDING)]
    )
    docs = await cursor.to_list(length=None)
    return _rows(docs)


async def delete_button(button_id: int) -> bool:
    result = await _btns().delete_one({"_id": button_id})
    return result.deleted_count > 0


async def clear_post_buttons(post_id: int):
    await _btns().delete_many({"post_id": post_id})


async def has_reaction_buttons(post_id: int) -> dict:
    buttons = await get_post_buttons(post_id)
    types = {b["button_type"] for b in buttons}
    return {
        "like":    "like"    in types,
        "dislike": "dislike" in types,
        "views":   "views"   in types,
        "share":   "share"   in types,
    }


async def get_next_row_for_post(post_id: int) -> int:
    """Get next available row number for a post."""
    pipeline = [
        {"$match": {"post_id": post_id}},
        {"$group": {"_id": None, "max_row": {"$max": "$row_num"}}},
    ]
    result = await _btns().aggregate(pipeline).to_list(length=1)
    if result:
        return result[0]["max_row"] + 1
    return 0


async def get_button_count_in_row(post_id: int, row_num: int) -> int:
    return await _btns().count_documents({"post_id": post_id, "row_num": row_num})


# ══════════════════════════════════════════════════════════
#   REACTION OPERATIONS  (post reactions)
# ══════════════════════════════════════════════════════════

async def handle_reaction(post_id: int, user_id: int, reaction: str) -> tuple[dict, str]:
    """
    Toggle a reaction on a post.
    Returns (counts_dict, action)
    action: 'added' | 'removed' | 'changed'
    """
    existing = await _rxns().find_one({"post_id": post_id, "user_id": user_id})

    # To maintain backward compatibility with old DB entries:
    def _field(r: str) -> str:
        if r == "like": return "likes"
        if r == "dislike": return "dislikes"
        return r

    if existing:
        old = existing["reaction"]
        if old == reaction:
            # Toggle off
            await _rxns().delete_one({"post_id": post_id, "user_id": user_id})
            await _rxc().update_one(
                {"_id": post_id},
                {"$inc": {_field(reaction): -1}},
                upsert=True
            )
            action = "removed"
        else:
            # Switch
            await _rxns().update_one(
                {"post_id": post_id, "user_id": user_id},
                {"$set": {"reaction": reaction}}
            )
            await _rxc().update_one(
                {"_id": post_id},
                {"$inc": {_field(old): -1, _field(reaction): 1}},
                upsert=True
            )
            action = "changed"
    else:
        # New reaction
        await _rxns().insert_one({
            "post_id":    post_id,
            "user_id":    user_id,
            "reaction":   reaction,
            "created_at": datetime.now(timezone.utc),
        })
        await _rxc().update_one(
            {"_id": post_id},
            {"$inc": {_field(reaction): 1}},
            upsert=True
        )
        action = "added"

    counts = await get_reaction_counts(post_id)
    return counts, action


async def get_user_reaction(post_id: int, user_id: int) -> str | None:
    doc = await _rxns().find_one({"post_id": post_id, "user_id": user_id})
    return doc["reaction"] if doc else None


async def increment_views(post_id: int) -> int:
    """Increment view count and return new count."""
    doc = await _rxc().find_one_and_update(
        {"_id": post_id},
        {"$inc": {"views": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc.get("views", 0)


async def get_reaction_counts(post_id: int) -> dict:
    c = await _rxc().find_one({"_id": post_id}) or {}
    
    # Ensure likes, dislikes, and views are always present as base keys
    res = {
        "likes": max(0, c.get("likes", 0)),
        "dislikes": max(0, c.get("dislikes", 0)),
        "views": max(0, c.get("views", 0)),
    }
    
    # Include any custom reactions
    for k, v in c.items():
        if k not in ("_id", "likes", "dislikes", "views"):
            res[k] = max(0, v)
            
    return res


# ══════════════════════════════════════════════════════════
#   SENT MESSAGE TRACKING
# ══════════════════════════════════════════════════════════

async def save_sent_message(post_id: int, chat_id: int = None,
                             message_id: int = None, inline_message_id: str = None):
    sent_id = await _next_id("sent_messages")
    await _sent().insert_one({
        "_id":               sent_id,
        "post_id":           post_id,
        "chat_id":           chat_id,
        "message_id":        message_id,
        "inline_message_id": inline_message_id,
        "created_at":        datetime.now(timezone.utc),
    })


async def get_sent_messages(post_id: int) -> list[dict]:
    cursor = _sent().find({"post_id": post_id})
    docs = await cursor.to_list(length=None)
    return _rows(docs)


# ══════════════════════════════════════════════════════════
#   USER CHANNELS
# ══════════════════════════════════════════════════════════

async def get_user_channels(user_id: int) -> list[dict]:
    cursor = _uchans().find({"user_id": user_id}).sort("created_at", ASCENDING)
    docs = await cursor.to_list(length=None)
    return _rows(docs)


async def add_user_channel(user_id: int, channel: str, title: str = None) -> bool:
    """Adds a channel. Returns True if added, False if already exists."""
    try:
        ch_id = await _next_id("user_channels")
        await _uchans().insert_one({
            "_id":                   ch_id,
            "user_id":               user_id,
            "channel_username_or_id": channel,
            "channel_title":         title,
            "created_at":            datetime.now(timezone.utc),
        })
        return True
    except Exception:
        return False


async def remove_user_channel(user_id: int, channel_id: int) -> bool:
    result = await _uchans().delete_one({"_id": channel_id, "user_id": user_id})
    return result.deleted_count > 0


async def count_user_channels(user_id: int) -> int:
    return await _uchans().count_documents({"user_id": user_id})


async def update_channel_title(row_id: int, title: str) -> None:
    await _uchans().update_one(
        {"_id": row_id},
        {"$set": {"channel_title": title}}
    )


# ══════════════════════════════════════════════════════════
#   GLOBAL BOT STATISTICS  (Admin /stats)
# ══════════════════════════════════════════════════════════

async def get_global_stats() -> dict:
    """Aggregate bot-wide statistics for /stats command."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # ── Users (from dedicated users collection) ───────────
    total_users = await _users().count_documents({})
    today_users = await _users().count_documents({"joined_at": {"$gte": today_start}})

    # ── Posts ────────────────────────────────────────────────
    total_posts = await _posts().count_documents({})
    posts_today = await _posts().count_documents({"created_at": {"$gte": today_start}})

    # ── Buttons ──────────────────────────────────────────────
    total_buttons = await _btns().count_documents({})
    url_buttons   = await _btns().count_documents({"button_type": "url"})
    like_buttons  = await _btns().count_documents({"button_type": "like"})
    view_buttons  = await _btns().count_documents({"button_type": "views"})
    share_buttons = await _btns().count_documents({"button_type": "share"})

    # ── Engagement (reaction_counts aggregate) ───────────────
    rxc_pipeline = [
        {"$group": {
            "_id":      None,
            "likes":    {"$sum": "$likes"},
            "dislikes": {"$sum": "$dislikes"},
            "views":    {"$sum": "$views"},
            "shares":   {"$sum": "$shares"},
        }}
    ]
    rxc_result = await _rxc().aggregate(rxc_pipeline).to_list(length=1)
    rxc = rxc_result[0] if rxc_result else {}
    total_likes    = rxc.get("likes", 0)
    total_dislikes = rxc.get("dislikes", 0)
    total_views    = rxc.get("views", 0)
    total_shares   = rxc.get("shares", 0)
    total_reactions = await _rxns().count_documents({})

    # ── Channels ─────────────────────────────────────────────
    total_saved_channels = await _uchans().count_documents({})
    total_sent_messages  = await _sent().count_documents({})

    # ── Auto Button Adder ────────────────────────────────────
    total_projects  = await _proj().count_documents({})
    active_projects = await _proj().count_documents({"is_active": True})
    ch_auto_reacted = await _chreact().count_documents({})

    # ── Top user (most posts) ─────────────────────────────────
    top_pipeline = [
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$sort":  {"count": -1}},
        {"$limit": 1},
    ]
    top_result = await _posts().aggregate(top_pipeline).to_list(length=1)
    top_user_id    = top_result[0]["_id"]    if top_result else None
    top_user_posts = top_result[0]["count"]  if top_result else 0

    return {
        "total_users":          total_users,
        "today_users":          today_users,
        "total_posts":          total_posts,
        "posts_today":          posts_today,
        "total_buttons":        total_buttons,
        "url_buttons":          url_buttons,
        "like_buttons":         like_buttons,
        "view_buttons":         view_buttons,
        "share_buttons":        share_buttons,
        "total_likes":          total_likes,
        "total_dislikes":       total_dislikes,
        "total_views":          total_views,
        "total_shares":         total_shares,
        "total_reactions":      total_reactions,
        "total_saved_channels": total_saved_channels,
        "total_sent_messages":  total_sent_messages,
        "total_projects":       total_projects,
        "active_projects":      active_projects,
        "ch_auto_reacted":      ch_auto_reacted,
        "top_user_id":          top_user_id,
        "top_user_posts":       top_user_posts,
    }


# ══════════════════════════════════════════════════════════
#   CHANNEL PROJECTS  (Auto Button Adder)
# ══════════════════════════════════════════════════════════

async def save_channel_project(user_id: int, channel_id: str,
                                channel_title: str, buttons_json: str) -> int:
    """Upsert a project for a channel. Returns the project id."""
    now = datetime.now(timezone.utc)
    existing = await _proj().find_one({"channel_id": channel_id})

    if existing:
        await _proj().update_one(
            {"channel_id": channel_id},
            {"$set": {
                "user_id":       user_id,
                "channel_title": channel_title,
                "buttons_json":  buttons_json,
                "is_active":     True,
                "created_at":    now,
            }}
        )
        return existing["_id"]
    else:
        proj_id = await _next_id("channel_projects")
        await _proj().insert_one({
            "_id":           proj_id,
            "user_id":       user_id,
            "channel_id":    channel_id,
            "channel_title": channel_title,
            "buttons_json":  buttons_json,
            "is_active":     True,
            "created_at":    now,
        })
        return proj_id


async def get_channel_project(channel_id: str) -> dict | None:
    """Get the active project for a channel."""
    doc = await _proj().find_one({"channel_id": channel_id, "is_active": True})
    return _row(doc)


async def get_user_projects(user_id: int) -> list[dict]:
    cursor = _proj().find({"user_id": user_id}).sort("created_at", DESCENDING)
    docs = await cursor.to_list(length=None)
    return _rows(docs)


async def delete_channel_project(user_id: int, project_id: int) -> bool:
    result = await _proj().delete_one({"_id": project_id, "user_id": user_id})
    return result.deleted_count > 0


async def toggle_channel_project(user_id: int, project_id: int, active: bool) -> None:
    await _proj().update_one(
        {"_id": project_id, "user_id": user_id},
        {"$set": {"is_active": active}}
    )


# ══════════════════════════════════════════════════════════
#   CHANNEL POST REACTIONS  (Auto Button Adder)
# ══════════════════════════════════════════════════════════

async def get_or_create_channel_reactions(channel_id: str, message_id: int) -> dict:
    """Return reaction counts for a channel post, creating if needed."""
    doc = await _chreact().find_one_and_update(
        {"channel_id": channel_id, "message_id": message_id},
        {"$setOnInsert": {"likes": 0, "dislikes": 0, "views": 0}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return {"likes": doc.get("likes", 0), "dislikes": doc.get("dislikes", 0), "views": doc.get("views", 0)}


async def get_channel_user_reaction(channel_id: str, message_id: int, user_id: int) -> str | None:
    doc = await _chureact().find_one({
        "channel_id": channel_id, "message_id": message_id, "user_id": user_id
    })
    return doc["reaction"] if doc else None


async def set_channel_user_reaction(channel_id: str, message_id: int,
                                     user_id: int, reaction: str) -> dict:
    """
    Toggle like/dislike for a channel post.
    Returns updated counts dict.
    """
    # Ensure reaction counts doc exists
    await _chreact().update_one(
        {"channel_id": channel_id, "message_id": message_id},
        {"$setOnInsert": {"likes": 0, "dislikes": 0, "views": 0}},
        upsert=True,
    )

    existing_doc = await _chureact().find_one({
        "channel_id": channel_id, "message_id": message_id, "user_id": user_id
    })
    existing = existing_doc["reaction"] if existing_doc else None

    # Backward compatibility helper
    def _field(r: str) -> str:
        if r == "like": return "likes"
        if r == "dislike": return "dislikes"
        return r

    if existing == reaction:
        # Toggle off
        await _chureact().delete_one({
            "channel_id": channel_id, "message_id": message_id, "user_id": user_id
        })
        await _chreact().update_one(
            {"channel_id": channel_id, "message_id": message_id},
            {"$inc": {_field(reaction): -1}}
        )
    elif existing:
        # Switch reaction
        await _chureact().update_one(
            {"channel_id": channel_id, "message_id": message_id, "user_id": user_id},
            {"$set": {"reaction": reaction}}
        )
        await _chreact().update_one(
            {"channel_id": channel_id, "message_id": message_id},
            {"$inc": {_field(existing): -1, _field(reaction): 1}}
        )
    else:
        # New reaction
        try:
            await _chureact().insert_one({
                "channel_id": channel_id,
                "message_id": message_id,
                "user_id":    user_id,
                "reaction":   reaction,
            })
        except Exception:
            pass  # Duplicate — race condition, ignore
        await _chreact().update_one(
            {"channel_id": channel_id, "message_id": message_id},
            {"$inc": {_field(reaction): 1}}
        )

    doc = await _chreact().find_one({"channel_id": channel_id, "message_id": message_id}) or {}
    res = {
        "likes": max(0, doc.get("likes", 0)),
        "dislikes": max(0, doc.get("dislikes", 0)),
        "views": max(0, doc.get("views", 0)),
    }
    for k, v in doc.items():
        if k not in ("_id", "likes", "dislikes", "views", "channel_id", "message_id"):
            res[k] = max(0, v)
    return res


async def add_channel_view(channel_id: str, message_id: int, user_id: int) -> dict:
    """Increment views for a channel post (one per user). Returns updated counts."""
    # Ensure counts doc exists
    await _chreact().update_one(
        {"channel_id": channel_id, "message_id": message_id},
        {"$setOnInsert": {"likes": 0, "dislikes": 0, "views": 0}},
        upsert=True,
    )
    # Only count unique views
    try:
        await _chureact().insert_one({
            "channel_id": channel_id,
            "message_id": message_id,
            "user_id":    user_id,
            "reaction":   "views",
        })
        # Successfully inserted → first view
        doc = await _chreact().find_one_and_update(
            {"channel_id": channel_id, "message_id": message_id},
            {"$inc": {"views": 1}},
            return_document=ReturnDocument.AFTER,
        )
    except Exception:
        # Already viewed — just fetch current counts
        doc = await _chreact().find_one({"channel_id": channel_id, "message_id": message_id})

    doc = doc or {}
    res = {
        "likes": max(0, doc.get("likes", 0)),
        "dislikes": max(0, doc.get("dislikes", 0)),
        "views": max(0, doc.get("views", 0)),
    }
    for k, v in doc.items():
        if k not in ("_id", "likes", "dislikes", "views", "channel_id", "message_id"):
            res[k] = max(0, v)
    return res
