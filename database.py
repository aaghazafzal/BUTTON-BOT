"""
╔══════════════════════════════════════════╗
║       DATABASE HANDLER — SQLite Async    ║
║   (MongoDB-ready — sirf URI set karo)    ║
╚══════════════════════════════════════════╝
"""

import aiosqlite
from datetime import datetime
from config import DB_PATH


# ═══════════════════════════════════════════
#              INITIALIZATION
# ═══════════════════════════════════════════

async def init_db():
    """Create all tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS posts (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                content_type  TEXT    NOT NULL,
                content       TEXT    NOT NULL,
                caption       TEXT,
                parse_mode    TEXT    DEFAULT 'HTML',
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS buttons (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id       INTEGER NOT NULL,
                button_type   TEXT    NOT NULL DEFAULT 'url',
                text          TEXT    NOT NULL,
                url           TEXT,
                callback_data TEXT,
                color         TEXT    DEFAULT 'default',
                row_num       INTEGER DEFAULT 0,
                order_num     INTEGER DEFAULT 0,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reactions (
                post_id    INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                reaction   TEXT    NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (post_id, user_id),
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reaction_counts (
                post_id   INTEGER PRIMARY KEY,
                likes     INTEGER DEFAULT 0,
                dislikes  INTEGER DEFAULT 0,
                views     INTEGER DEFAULT 0,
                shares    INTEGER DEFAULT 0,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sent_messages (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id           INTEGER NOT NULL,
                chat_id           INTEGER,
                message_id        INTEGER,
                inline_message_id TEXT,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                user_id           INTEGER PRIMARY KEY,
                default_color     TEXT DEFAULT 'default',
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_channels (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id                INTEGER NOT NULL,
                channel_username_or_id TEXT NOT NULL,
                channel_title          TEXT DEFAULT NULL,
                created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, channel_username_or_id)
            );

            CREATE TABLE IF NOT EXISTS channel_projects (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                channel_id    TEXT NOT NULL,
                channel_title TEXT,
                buttons_json  TEXT NOT NULL DEFAULT '[]',
                is_active     INTEGER DEFAULT 1,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(channel_id)
            );

            CREATE TABLE IF NOT EXISTS channel_post_reactions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                likes      INTEGER DEFAULT 0,
                dislikes   INTEGER DEFAULT 0,
                views      INTEGER DEFAULT 0,
                UNIQUE(channel_id, message_id)
            );

            CREATE TABLE IF NOT EXISTS channel_post_user_reactions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                reaction   TEXT NOT NULL,
                UNIQUE(channel_id, message_id, user_id)
            );
        """)
        # Migration: add channel_title column if it doesn't exist yet (safe for old DBs)
        try:
            await db.execute("ALTER TABLE user_channels ADD COLUMN channel_title TEXT DEFAULT NULL")
            await db.commit()
        except Exception:
            pass  # Column already exists — no problem


# ═══════════════════════════════════════════
#              POST OPERATIONS
# ═══════════════════════════════════════════

async def create_post(user_id: int, content_type: str, content: str, caption: str = None) -> int:
    """Create a new post. Returns post_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO posts (user_id, content_type, content, caption) VALUES (?, ?, ?, ?)",
            (user_id, content_type, content, caption)
        )
        post_id = cursor.lastrowid
        await db.execute(
            "INSERT INTO reaction_counts (post_id, likes, dislikes, views, shares) VALUES (?, 0, 0, 0, 0)",
            (post_id,)
        )
        await db.commit()
        return post_id


async def get_post(post_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_posts(user_id: int, limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT p.*, rc.likes, rc.dislikes, rc.views FROM posts p "
            "LEFT JOIN reaction_counts rc ON p.id = rc.post_id "
            "WHERE p.user_id = ? ORDER BY p.created_at DESC LIMIT ?",
            (user_id, limit)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def count_user_posts(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM posts WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def delete_post(post_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM posts WHERE id = ? AND user_id = ?", (post_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_post_content(post_id: int, content: str, caption: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE posts SET content = ?, caption = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (content, caption, post_id)
        )
        await db.commit()


# ═══════════════════════════════════════════
#              BUTTON OPERATIONS
# ═══════════════════════════════════════════

async def add_button(post_id: int, button_type: str, text: str,
                     url: str = None, callback_data: str = None,
                     color: str = 'default', row_num: int = 0, order_num: int = 0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO buttons
               (post_id, button_type, text, url, callback_data, color, row_num, order_num)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (post_id, button_type, text, url, callback_data, color, row_num, order_num)
        )
        await db.commit()
        return cursor.lastrowid


async def get_post_buttons(post_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM buttons WHERE post_id = ? ORDER BY row_num, order_num",
            (post_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def delete_button(button_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM buttons WHERE id = ?", (button_id,))
        await db.commit()
        return cursor.rowcount > 0


async def clear_post_buttons(post_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM buttons WHERE post_id = ?", (post_id,))
        await db.commit()


async def has_reaction_buttons(post_id: int) -> dict:
    """Returns {'like': bool, 'dislike': bool, 'views': bool}"""
    buttons = await get_post_buttons(post_id)
    types = {b['button_type'] for b in buttons}
    return {
        'like': 'like' in types,
        'dislike': 'dislike' in types,
        'views': 'views' in types,
        'share': 'share' in types,
    }


async def get_next_row_for_post(post_id: int) -> int:
    """Get next available row number for a post."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COALESCE(MAX(row_num), -1) + 1 FROM buttons WHERE post_id = ?",
            (post_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_button_count_in_row(post_id: int, row_num: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM buttons WHERE post_id = ? AND row_num = ?",
            (post_id, row_num)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


# ═══════════════════════════════════════════
#            REACTION OPERATIONS
# ═══════════════════════════════════════════

async def handle_reaction(post_id: int, user_id: int, reaction: str) -> tuple[int, int, str]:
    """
    Toggle like/dislike.
    Returns (new_likes, new_dislikes, action)
    action: 'added' | 'removed' | 'changed'
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute(
            "SELECT reaction FROM reactions WHERE post_id = ? AND user_id = ?",
            (post_id, user_id)
        ) as cur:
            existing = await cur.fetchone()

        if existing:
            if existing['reaction'] == reaction:
                # Same reaction — remove (toggle off)
                await db.execute(
                    "DELETE FROM reactions WHERE post_id = ? AND user_id = ?",
                    (post_id, user_id)
                )
                action = 'removed'
            else:
                # Different — switch reaction
                await db.execute(
                    "UPDATE reactions SET reaction = ? WHERE post_id = ? AND user_id = ?",
                    (reaction, post_id, user_id)
                )
                action = 'changed'
        else:
            await db.execute(
                "INSERT INTO reactions (post_id, user_id, reaction) VALUES (?, ?, ?)",
                (post_id, user_id, reaction)
            )
            action = 'added'

        await db.commit()

        # Recalculate counts
        async with db.execute(
            "SELECT reaction, COUNT(*) as cnt FROM reactions WHERE post_id = ? GROUP BY reaction",
            (post_id,)
        ) as cur:
            counts = {r['reaction']: r['cnt'] for r in await cur.fetchall()}

        likes = counts.get('like', 0)
        dislikes = counts.get('dislike', 0)

        await db.execute(
            "UPDATE reaction_counts SET likes = ?, dislikes = ? WHERE post_id = ?",
            (likes, dislikes, post_id)
        )
        await db.commit()

        return likes, dislikes, action


async def get_user_reaction(post_id: int, user_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT reaction FROM reactions WHERE post_id = ? AND user_id = ?",
            (post_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def increment_views(post_id: int) -> int:
    """Increment view count and return new count."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE reaction_counts SET views = views + 1 WHERE post_id = ?",
            (post_id,)
        )
        await db.commit()
        async with db.execute(
            "SELECT views FROM reaction_counts WHERE post_id = ?", (post_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_reaction_counts(post_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT likes, dislikes, views, shares FROM reaction_counts WHERE post_id = ?",
            (post_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {'likes': 0, 'dislikes': 0, 'views': 0, 'shares': 0}


# ═══════════════════════════════════════════
#         SENT MESSAGE TRACKING
# ═══════════════════════════════════════════

async def save_sent_message(post_id: int, chat_id: int = None,
                             message_id: int = None, inline_message_id: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sent_messages (post_id, chat_id, message_id, inline_message_id) VALUES (?, ?, ?, ?)",
            (post_id, chat_id, message_id, inline_message_id)
        )
        await db.commit()


async def get_sent_messages(post_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sent_messages WHERE post_id = ?", (post_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

# ═══════════════════════════════════════════
#             USER CHANNELS
# ═══════════════════════════════════════════

async def get_user_channels(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM user_channels WHERE user_id = ? ORDER BY created_at ASC", (user_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def add_user_channel(user_id: int, channel: str, title: str = None) -> bool:
    """Adds a channel with optional display title. Returns True if added."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO user_channels (user_id, channel_username_or_id, channel_title) VALUES (?, ?, ?)",
                (user_id, channel, title)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def remove_user_channel(user_id: int, channel_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM user_channels WHERE user_id = ? AND id = ?",
            (user_id, channel_id)
        )
        await db.commit()
        return cursor.rowcount > 0

async def count_user_channels(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM user_channels WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

async def update_channel_title(row_id: int, title: str) -> None:
    """Update the display title for a saved channel row."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE user_channels SET channel_title = ? WHERE id = ?",
            (title, row_id)
        )
        await db.commit()


# ═══════════════════════════════════════════
#           CHANNEL PROJECTS (Auto Button Adder)
# ═══════════════════════════════════════════

async def save_channel_project(user_id: int, channel_id: str,
                                channel_title: str, buttons_json: str) -> int:
    """Insert or replace a project for a channel. Returns the row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO channel_projects (user_id, channel_id, channel_title, buttons_json)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(channel_id) DO UPDATE SET
                 user_id=excluded.user_id,
                 channel_title=excluded.channel_title,
                 buttons_json=excluded.buttons_json,
                 is_active=1,
                 created_at=CURRENT_TIMESTAMP""",
            (user_id, channel_id, channel_title, buttons_json)
        )
        await db.commit()
        return cursor.lastrowid


async def get_channel_project(channel_id: str) -> dict | None:
    """Get the active project for a channel (any user)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM channel_projects WHERE channel_id = ? AND is_active = 1",
            (channel_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_projects(user_id: int) -> list[dict]:
    """Get all projects owned by the user."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM channel_projects WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def delete_channel_project(user_id: int, project_id: int) -> bool:
    """Delete a project owned by the user."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM channel_projects WHERE id = ? AND user_id = ?",
            (project_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def toggle_channel_project(user_id: int, project_id: int, active: bool) -> None:
    """Enable or disable a project."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE channel_projects SET is_active = ? WHERE id = ? AND user_id = ?",
            (1 if active else 0, project_id, user_id)
        )
        await db.commit()


# ═══════════════════════════════════════════
#      CHANNEL POST REACTIONS  (Auto Button Adder)
# ═══════════════════════════════════════════

async def get_or_create_channel_reactions(channel_id: str, message_id: int) -> dict:
    """Return reaction counts for a channel post, creating the row if needed."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT OR IGNORE INTO channel_post_reactions (channel_id, message_id) VALUES (?, ?)",
            (channel_id, message_id)
        )
        await db.commit()
        async with db.execute(
            "SELECT likes, dislikes, views FROM channel_post_reactions WHERE channel_id=? AND message_id=?",
            (channel_id, message_id)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {"likes": 0, "dislikes": 0, "views": 0}


async def get_channel_user_reaction(channel_id: str, message_id: int, user_id: int) -> str | None:
    """Return the user's existing reaction ('like'|'dislike'|'views') or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT reaction FROM channel_post_user_reactions WHERE channel_id=? AND message_id=? AND user_id=?",
            (channel_id, message_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def set_channel_user_reaction(channel_id: str, message_id: int,
                                     user_id: int, reaction: str) -> dict:
    """
    Toggle like/dislike for a channel post. Returns new counts dict.
    - If user already reacted with SAME reaction → remove it (toggle off)
    - If user reacted with DIFFERENT reaction → switch
    - If no prior reaction → add it
    Only like/dislike are togglable; views are additive (one per user).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Ensure reaction row exists
        await db.execute(
            "INSERT OR IGNORE INTO channel_post_reactions (channel_id, message_id) VALUES (?, ?)",
            (channel_id, message_id)
        )
        existing = None
        async with db.execute(
            "SELECT reaction FROM channel_post_user_reactions WHERE channel_id=? AND message_id=? AND user_id=?",
            (channel_id, message_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            existing = row[0] if row else None

        if existing == reaction:
            # Toggle off
            await db.execute(
                "DELETE FROM channel_post_user_reactions WHERE channel_id=? AND message_id=? AND user_id=?",
                (channel_id, message_id, user_id)
            )
            col = "likes" if reaction == "like" else "dislikes"
            await db.execute(
                f"UPDATE channel_post_reactions SET {col} = MAX(0, {col} - 1) WHERE channel_id=? AND message_id=?",
                (channel_id, message_id)
            )
        elif existing:
            # Switch reaction
            await db.execute(
                "UPDATE channel_post_user_reactions SET reaction=? WHERE channel_id=? AND message_id=? AND user_id=?",
                (reaction, channel_id, message_id, user_id)
            )
            old_col = "likes" if existing == "like" else "dislikes"
            new_col = "likes" if reaction == "like" else "dislikes"
            await db.execute(
                f"UPDATE channel_post_reactions SET {old_col}=MAX(0,{old_col}-1), {new_col}={new_col}+1 WHERE channel_id=? AND message_id=?",
                (channel_id, message_id)
            )
        else:
            # New reaction
            await db.execute(
                "INSERT INTO channel_post_user_reactions (channel_id, message_id, user_id, reaction) VALUES (?,?,?,?)",
                (channel_id, message_id, user_id, reaction)
            )
            col = "likes" if reaction == "like" else "dislikes"
            await db.execute(
                f"UPDATE channel_post_reactions SET {col}={col}+1 WHERE channel_id=? AND message_id=?",
                (channel_id, message_id)
            )

        await db.commit()
        async with db.execute(
            "SELECT likes, dislikes, views FROM channel_post_reactions WHERE channel_id=? AND message_id=?",
            (channel_id, message_id)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {"likes": 0, "dislikes": 0, "views": 0}


async def add_channel_view(channel_id: str, message_id: int, user_id: int) -> dict:
    """
    Increment views for a channel post (one per user).
    Returns updated counts.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT OR IGNORE INTO channel_post_reactions (channel_id, message_id) VALUES (?, ?)",
            (channel_id, message_id)
        )
        # Only count if not already viewed
        async with db.execute(
            "SELECT 1 FROM channel_post_user_reactions WHERE channel_id=? AND message_id=? AND user_id=? AND reaction='views'",
            (channel_id, message_id, user_id)
        ) as cur:
            already = await cur.fetchone()
        if not already:
            await db.execute(
                "INSERT OR IGNORE INTO channel_post_user_reactions (channel_id, message_id, user_id, reaction) VALUES (?,?,?,'views')",
                (channel_id, message_id, user_id)
            )
            await db.execute(
                "UPDATE channel_post_reactions SET views=views+1 WHERE channel_id=? AND message_id=?",
                (channel_id, message_id)
            )
        await db.commit()
        async with db.execute(
            "SELECT likes, dislikes, views FROM channel_post_reactions WHERE channel_id=? AND message_id=?",
            (channel_id, message_id)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {"likes": 0, "dislikes": 0, "views": 0}
