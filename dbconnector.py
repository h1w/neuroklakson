import asyncio
import aiosqlite

dbfilename = 'database.db'

async def createTable():
    async with aiosqlite.connect(dbfilename) as db:
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
    async with aiosqlite.connect(dbfilename) as db:
        await db.execute(
            "INSERT INTO messages (chat_id, message) VALUES (?, ?)",
            (chat_id, message)
        )
        await db.commit()
        await db.close()

async def insertMessages(chat_id, messages_list):
    async with aiosqlite.connect(dbfilename) as db:
        for message in messages_list:
            await db.execute(
                "INSERT INTO messages (chat_id, message) VALUES (?, ?)",
                (chat_id, message)
            )
        await db.commit()
        await db.close()

async def insertPhoto(chat_id, file_id):
    async with aiosqlite.connect(dbfilename) as db:
        await db.execute(
            "INSERT INTO photoes (chat_id, file_id) VALUES (?, ?)",
            (chat_id, file_id)
        )
        await db.commit()
        await db.close()

async def getRandomPhoto(chat_id):
    async with aiosqlite.connect(dbfilename) as db:
        async with db.execute(
            "SELECT file_id FROM photoes WHERE chat_id = ? ORDER BY RANDOM() LIMIT 1",
            (chat_id,)
        ) as cursor:
            random_photo_file_id = await cursor.fetchone()
        
        await db.close()
    
    return random_photo_file_id[0]

async def getRandomMessage(chat_id):
    async with aiosqlite.connect(dbfilename) as db:
        async with db.execute(
            "SELECT message FROM messages WHERE chat_id = ? ORDER BY RANDOM() LIMIT 1",
            (chat_id,)
        ) as cursor:
            random_message = await cursor.fetchone()
        
        await db.close()
    
    return random_message[0]

async def getAllMessages(chat_id):
    async with aiosqlite.connect(dbfilename) as db:
        async with db.execute(
            "SELECT message FROM messages WHERE chat_id = ?",
            (chat_id, )
        ) as cursor:
            all_messages = await cursor.fetchall()
        
        await db.close()
    
    return list(map(lambda x: ''.join(x), all_messages))