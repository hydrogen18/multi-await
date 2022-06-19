import multi_await
import aiohttp
import asyncio

async def async_main():
  urls = ['http://archive.org', 'http://localhost', 'http://fsf.org']
  async with aiohttp.ClientSession() as session:
    for task in multi_await.as_completed_or_abort([asyncio.create_task(session.get(x)) for x in urls]):
      result = await task
      await result.read()
      print(result.status)

asyncio.run(async_main())



