import aiosqlite

class Database:
    def __init__(self, db_file="forwarder.db"):
        self.db_file = db_file

    async def init(self):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    target_topic_id INTEGER DEFAULT NULL,
                    filter_type TEXT DEFAULT 'all',
                    remove_caption BOOLEAN DEFAULT 0,
                    custom_footer TEXT DEFAULT NULL,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            await db.commit()

    async def add_task(self, source_id: int, target_id: int, target_topic_id: int = None, filter_type: str = "all", remove_caption: bool = False, custom_footer: str = None):
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute("""
                INSERT INTO tasks (source_id, target_id, target_topic_id, filter_type, remove_caption, custom_footer)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (source_id, target_id, target_topic_id, filter_type, remove_caption, custom_footer))
            await db.commit()
            return cursor.lastrowid

    async def get_tasks_by_source(self, source_id: int):
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM tasks WHERE source_id = ? AND is_active = 1", (source_id,)) as cursor:
                return await cursor.fetchall()
