import asyncio
import aiotk

async def gather_or_abort(*tasks):
  '''Equivalent to asyncio.gather, but only works with Task objects. All tasks are cancelled when an
  exception occurs.
  '''
  try:
    return await asyncio.gather(*tasks)
  except BaseException:
    await aiotk.cancel_all(tasks)
    raise

async def wait_or_abort(tasks, timeout=None):
  '''Replacement for asyncio.wait, only works with Task objects. All tasks are cancelled when an exception occurs.
  When all tasks are completed a set of all tasks are returned'''
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
  '''Replacement for asyncio.as_completed, only works with Task objects. Instead of returning an iterator of coroutines,
  this is an async iterator that returns values as each one is completed. All tasks are cancelled with an exception
  occurs'''
  try:
    for f in asyncio.as_completed(tasks, timeout=timeout):
      yield await f
  except BaseException:
    await aiotk.cancel_all(tasks)
    raise

async def with_value(value, awaitable):
  '''Awaits the awaitable, returning the value from it and value in a tuple. Used for pairing the result of a task
  with an identifying value'''
  result = await awaitable
  return (value, result,)