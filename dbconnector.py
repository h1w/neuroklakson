import asyncio
import aiosqlite

async def createTable():
    async with aiosqlite.connect('database.db') as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS photoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        
        await db.commit()
        await db.close()
    
async def insertMessage(chat_id, message):
    async with aiosqlite.connect('database.db') as db:
        await db.execute(
            "INSERT INTO messages (chat_id, message) VALUES (?, ?)",
            (chat_id, message)
        )
        await db.commit()
        await db.close()

async def insertPhoto(chat_id, file_id):
    async with aiosqlite.connect('database.db') as db:
        await db.execute(
            "INSERT INTO photoes (chat_id, file_id) VALUES (?, ?)",
            (chat_id, file_id)
        )
        await db.commit()
        await db.close()

# async def selectMessages():
#     async with aiosqlite.connect("database.db") as db:
#         async with db.execute("SELECT * FROM messages") as cursor:
#             async for row in cursor:
#                 print(row)

# async def main():
#     await createTable()

# if __name__ == "__main__":
#     asyncio.run(main())

