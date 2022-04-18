import asyncio
import aiotk

async def gather_or_abort(*tasks):
  try:
    return await asyncio.gather(*tasks)
  except BaseException:
    await aiotk.cancel_all(tasks)
    raise

async def wait_or_abort(tasks, timeout=None):
  try:
    done, pending = await asyncio.wait(tasks, timeout=timeout, return_when=asyncio.FIRST_EXCEPTION)
    if len(pending) == 0:  # check if everything is done
      return done

    # Cancel anything still running
    await aiotk.cancel_all(tasks)
  except BaseException:
    await aiotk.cancel_all(tasks)
    raise

  # Try and find the exception and allow it to propagate
  for t in tasks:
    if not t.cancelled():
      await t

  # All tasks were cancelled, so this is a timeout condition
  raise asyncio.TimeoutError()

async def as_completed_or_abort(tasks, timeout=None):
  try:
    for f in asyncio.as_completed(tasks, timeout=timeout):
      yield await f
  except BaseException:
    await aiotk.cancel_all(tasks)
    raise

async def with_value(value, awaitable):
  result = await awaitable
  return (value, result,)