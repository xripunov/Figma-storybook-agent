import sqlite3
import os

DB_FILE = "chat_history.db"

def init_db():
    print(f"Initializing database: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        "id" TEXT PRIMARY KEY,
        "identifier" TEXT NOT NULL UNIQUE,
        "createdAt" TEXT NOT NULL,
        "metadata" TEXT
    )''')

    # Threads
    c.execute('''CREATE TABLE IF NOT EXISTS threads (
        "id" TEXT PRIMARY KEY,
        "createdAt" TEXT NOT NULL,
        "name" TEXT,
        "userId" TEXT,
        "userIdentifier" TEXT,
        "tags" TEXT,
        "metadata" TEXT,
        FOREIGN KEY("userId") REFERENCES users("id") ON DELETE CASCADE
    )''')

    # Steps
    c.execute('''CREATE TABLE IF NOT EXISTS steps (
        "id" TEXT PRIMARY KEY,
        "name" TEXT NOT NULL,
        "type" TEXT NOT NULL,
        "threadId" TEXT NOT NULL,
        "parentId" TEXT,
        "streaming" BOOLEAN,
        "waitForAnswer" BOOLEAN,
        "isError" BOOLEAN,
        "metadata" TEXT,
        "tags" TEXT,
        "input" TEXT,
        "output" TEXT,
        "createdAt" TEXT,
        "start" TEXT,
        "end" TEXT,
        "generation" TEXT,
        "showInput" TEXT,
        "language" TEXT,
        "defaultOpen" BOOLEAN,
        FOREIGN KEY("threadId") REFERENCES threads("id") ON DELETE CASCADE
    )''')

    # Elements
    c.execute('''CREATE TABLE IF NOT EXISTS elements (
        "id" TEXT PRIMARY KEY,
        "threadId" TEXT,
        "type" TEXT,
        "chainlitKey" TEXT,
        "url" TEXT,
        "objectKey" TEXT,
        "name" TEXT,
        "display" TEXT,
        "size" TEXT,
        "language" TEXT,
        "page" TEXT,
        "forId" TEXT,
        "mime" TEXT,
        "props" TEXT,
        "autoPlay" BOOLEAN,
        "playerConfig" TEXT,
        FOREIGN KEY("threadId") REFERENCES threads("id") ON DELETE CASCADE
    )''')

    # Feedbacks
    c.execute('''CREATE TABLE IF NOT EXISTS feedbacks (
        "id" TEXT PRIMARY KEY,
        "forId" TEXT NOT NULL,
        "value" INTEGER NOT NULL,
        "comment" TEXT,
        FOREIGN KEY("forId") REFERENCES steps("id") ON DELETE CASCADE
    )''')

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
