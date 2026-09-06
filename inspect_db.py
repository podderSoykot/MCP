import asyncio

from sqlalchemy import text

from model.database import engine


async def inspect_database():
    async with engine.connect() as conn:

        result = await conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
        )

        tables = result.fetchall()

        print("\n=== TABLES ===")

        for table in tables:
            print(table[0])


if __name__ == "__main__":
    asyncio.run(inspect_database())
