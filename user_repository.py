import aiosqlite


# менеджер для асинхронных сессий
class DatabaseSession:
    def __init__(self, db_path):
        self.db_path = db_path

    async def __aenter__(self):
        self.conn = await aiosqlite.connect(self.db_path)
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()


# инициализация бд
async def init_db():
    async with DatabaseSession("study.db") as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        chat_id TEXT NOT NULL,
                        task TEXT NOT NULL)''')
        await db.commit()


class UserRepository:
    def __init__(self, db_path="study.db"):
        self.db_path = db_path

    async def get_user_tasks(self, chat_id: str) -> list[str]:
        async with DatabaseSession(self.db_path) as db:
            async with db.execute("SELECT task FROM users WHERE chat_id = ? ORDER BY rowid", (chat_id,)) as cursor:
                return [task[0] for task in await cursor.fetchall()]

    async def add_user_task(self, chat_id: str, task_text: str) -> tuple[bool, str]:
        try:
            async with DatabaseSession(self.db_path) as db:
                await db.execute("INSERT INTO users (chat_id, task) VALUES (?, ?)", (chat_id, task_text))
                await db.commit()
                return True, f"Задача '{task_text}' успешно добавлена"
        except aiosqlite.IntegrityError:
            return False, "Ошибка при добавлении задачи"

    async def delete_user_task(self, chat_id: str, task_number_to_delete: int) -> tuple[bool, str]:
        if task_number_to_delete > 0:
            async with DatabaseSession(self.db_path) as db:
                async with db.execute("SELECT task FROM users WHERE chat_id = ? ORDER BY rowid", (chat_id,)) as cursor:
                    tasks = await cursor.fetchall()
                if not tasks or len(tasks) < task_number_to_delete:
                    return False, "У вас нет такой задачи"
                task_text_to_delete = tasks[task_number_to_delete - 1][0]
                await db.execute("DELETE FROM users WHERE chat_id = ? AND task = ?", (chat_id, task_text_to_delete))
                await db.commit()
                return True, task_text_to_delete
        else:
            return False, "Неверный номер задачи"