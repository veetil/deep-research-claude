#!/usr/bin/env python3
import asyncio

async def main():
    print("Async test running")
    await asyncio.sleep(0.1)
    print("Async test complete")

if __name__ == "__main__":
    print("Starting...")
    asyncio.run(main())
    print("Done")