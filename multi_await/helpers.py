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

  done, pending = await asyncio.wait(tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
  if len(pending) == 0:  # check if everything is done
    return done

  # Cancel anything still running
  await aiotk.cancel_all(pending)

  # Try and find the exception and allow it to propagate
  for t in done:
      await t

  # All tasks were cancelled, so this is a timeout condition
  raise asyncio.TimeoutError()

def as_completed_or_abort(tasks, timeout=None):
  '''Replacement for asyncio.as_completed, only works with Task objects. Instead of returning an iterator of coroutines,
  this is an async iterator that returns values as each one is completed. All tasks are cancelled with an exception
  occurs'''

  completed_iterator = asyncio.as_completed(tasks, timeout=timeout)
  remaining = len(tasks)
  async def _one_completed_or_abort():
    nonlocal remaining
    next_item = next(completed_iterator)
    try:
      result = await next_item
    except BaseException as exc:
      failure = exc
      result = None
    else:
      failure = None

    if failure is None:
      return result

    remaining = 0
    await aiotk.cancel_all(tasks)
    raise failure

  while remaining > 0:
    yield _one_completed_or_abort()
    remaining -= 1

async def with_value(value, awaitable):
  '''Awaits the awaitable, returning the value from it and value in a tuple. Used for pairing the result of a task
  with an identifying value'''

  result = await awaitable
  return (value, result,)