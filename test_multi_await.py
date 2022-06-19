import functools
import asyncio
import random
from multi_await import *

async def raise_exception():
  int('z')

async def return_value():
  return 1

async def return_a_value(v):
  return v

async def sleep_random():
  await asyncio.sleep(0.1 + random.random())
  return 'sleep'

async def sleep_and_return(duration, v):
  await asyncio.sleep(duration)
  return v
  
async def run_forever():
  while True:
    await asyncio.sleep(9999.0)

async def return_value_as_task():
  return 2
  
async def push_even_numbers(q):
  for i in range(100):
    if i % 2 == 0:
      await q.put(i)
      
async def push_odd_numbers(q):
  for i in range(100):
    if i % 2 == 1:
      await q.put(i)

# --- Tests 

async def test_can_get_a_value():
  async with multi_await() as m:    
    m.add(return_value)
  
    results, failures = await m.get()

    assert results == [1]
    assert failures == [None]
    
async def test_can_get_a_value_from_a_task():
  async with multi_await() as m:    
    m.add(return_value_as_task)
  
    results, failures = await m.get()

    assert results == [2] 
    assert failures == [None]
 
async def test_can_get_an_exception(): 
  async with multi_await() as m:   
    m.add(raise_exception)
  
    results, failures = await m.get()

    assert results == [None]   
    assert isinstance(failures[0], ValueError)
    
async def test_can_get_an_exception_first(): 
  async with multi_await() as m:     
    m.add(raise_exception)
    m.add(run_forever)
  
    results, failures = await m.get()

    assert results == [None, None]   
    assert isinstance(failures[0], ValueError)
    assert failures[1] is None
    await  m.cancel() 
    
async def test_can_get_a_value_with_another_coro_that_never_returns():
  async with multi_await() as m: 
    m.add(return_value)
    m.add(run_forever)
  
    results, failures = await m.get()

    assert results == [1, None]   
    assert failures == [None, None]
    
async def test_can_get_exception_and_value():
  async with multi_await() as m:
    m.add(return_value)
    m.add(raise_exception)
    
    results, failures = await m.get()
    assert results == [1, None]
    assert failures[0] is None
    assert isinstance(failures[1], ValueError)
    
async def test_can_run_the_same_tasks_multiple_times():
  # Start some queues with differing capacities
  odd_queue = asyncio.Queue(1)
  even_queue = asyncio.Queue(2)
  numbers = []

  # Start some tasks to feed stuff into the queue
  tasks = [ asyncio.create_task(push_odd_numbers(odd_queue)), asyncio.create_task(push_even_numbers(even_queue))]  
  
  async with multi_await() as m:
    m.add(odd_queue.get)
    m.add(even_queue.get)
    m.add(run_forever) # Does nothing in the test, just like the others
    
    done = False
    while not done:
      results, failures = await m.get()
      assert failures == [None, None, None]
      for r in results:
        if r is not None:
          numbers.append(r)
        
      done = len(numbers) >= 100
      
  assert list(range(100)) == sorted(numbers)
  
  [await t for t in tasks] # Cleanup after the test
    
async def test_fails_if_nothing_to_do():
  async with multi_await() as m:
    try:
      await m.get()
    except RuntimeError as e:
      assert str(e) == 'Attempted to await 0 coroutines'

async def test_gather_or_abort():
  tasks = [asyncio.create_task(x) for x in (return_a_value(1), return_a_value(2), return_a_value(3),)]
  a, b, c = await gather_or_abort(*tasks)
  assert a == 1
  assert b == 2
  assert c == 3

async def test_gather_or_abort_cancel():
  tasks = [asyncio.create_task(x) for x in (sleep_and_return(5.0, 1), sleep_and_return(5.0, 2), sleep_and_return(5.0, 3))]
  tested_task = asyncio.create_task(gather_or_abort(*tasks))
  tasks[0].cancel()

  try:
    await tested_task
    assert False
  except asyncio.CancelledError:
    pass

  assert tasks[1].cancelled()
  assert tasks[2].cancelled()

async def test_gather_or_abort_exception():
  exception_task = asyncio.create_task(raise_exception())
  sleep_tasks = [asyncio.create_task(run_forever()) for _ in range (3)]
  try:
    await gather_or_abort(exception_task, *sleep_tasks)
  except ValueError as exc:
    assert exc is not None
  else:
    assert False

  for t in sleep_tasks:
    assert t.cancelled()

  assert exception_task.done()
  assert exception_task.exception() is not None
  assert not exception_task.cancelled()

async def test_wait_or_abort():
  tasks = [asyncio.create_task(x) for x in (return_a_value(1), return_a_value(2), return_a_value(3),)]
  done = await wait_or_abort(tasks)
  assert len(done) == 3

  result = set([await x for x in done])
  assert 1 in result
  assert 2 in result
  assert 3 in result

async def test_wait_or_abort_timeout():
  sleep_task = asyncio.create_task(asyncio.sleep(9999))
  value_tasks = [asyncio.create_task(x) for x in (return_a_value(1), return_a_value(2), return_a_value(3))]
  tasks = value_tasks + [sleep_task]
  try:
    await wait_or_abort(tasks, timeout=0.1)
  except asyncio.TimeoutError as exc:
    assert exc is not None
  else:
    assert False

  assert sleep_task.cancelled()

  for t in value_tasks:
    assert t.done()

async def test_wait_or_abort_cancel():
  tasks = [asyncio.create_task(x) for x in (sleep_and_return(5.0, 1), sleep_and_return(5.0, 2), sleep_and_return(5.0, 3))]

  tested_task = asyncio.create_task(wait_or_abort(tasks))
  tasks[0].cancel()

  try:
    await tested_task
    assert False
  except asyncio.CancelledError:
    pass

  assert tasks[1].cancelled()
  assert tasks[2].cancelled()

async def test_wait_or_abort_exception():
  exception_task = asyncio.create_task(raise_exception())
  sleep_tasks = [asyncio.create_task(run_forever()) for _ in range (3)]
  try:
    # Set timeout here, even with that present the exception from the task should be returned
    await wait_or_abort([exception_task] + sleep_tasks, timeout=0.0)
  except ValueError as exc:
    assert exc is not None
  else:
    assert False

  for t in sleep_tasks:
    assert t.cancelled()

  assert exception_task.done()
  assert exception_task.exception() is not None
  assert not exception_task.cancelled()

async def test_as_completed_or_abort():
  tasks = [asyncio.create_task(x) for x in (return_a_value(1), return_a_value(2), return_a_value(3),)]
  result = set()
  for x in as_completed_or_abort(tasks):
    result.add(await x)
  assert result == {1,2,3}

async def test_as_completed_or_abort_exception():
  exception_task = asyncio.create_task(raise_exception())
  sleep_tasks = [asyncio.create_task(asyncio.sleep(999)) for _ in range(3)]
  tasks = [exception_task] + sleep_tasks

  completed_cnt = 0
  for x in as_completed_or_abort(tasks):
    completed_cnt += 1
    try:
      y = await x
    except ValueError as exc:
      assert exc is not None
    else:
      assert False
  assert completed_cnt == 1

  for t in sleep_tasks:
    assert t.cancelled()

  assert exception_task.done()
  assert exception_task.exception() is not None
  assert not exception_task.cancelled()

async def test_as_completed_timeout():
  sleep_task = asyncio.create_task(asyncio.sleep(999))
  for x in as_completed_or_abort([sleep_task], timeout=0.1):
    try:
      await x
    except asyncio.TimeoutError as exc:
      assert exc is not None
    else:
      assert False

  assert sleep_task.cancelled()

async def test_as_completed_cancel():
  tasks = [asyncio.create_task(x) for x in (sleep_and_return(5.0, 1), sleep_and_return(5.0, 2), sleep_and_return(5.0, 3))]
  tasks[0].cancel()
  for x in as_completed_or_abort(tasks):
    try:
      await x
    except asyncio.CancelledError:
      pass
    else:
      assert False

  assert tasks[1].cancelled()
  assert tasks[2].cancelled()

async def test_as_completed_timeout_many():
  sleep_task = asyncio.create_task(asyncio.sleep(999))
  value_tasks = [asyncio.create_task(sleep_and_return(0.01,x)) for x in range(3)]
  values = set()

  for x in as_completed_or_abort([sleep_task] + value_tasks,timeout=0.3):
    try:
      values.add(await x)
    except asyncio.TimeoutError as exc:
      assert exc is not None

  assert sleep_task.cancelled()
  assert values == {0,1,2}

for entry in dir():
  if not entry.startswith('test_'):
    continue

  el = asyncio.new_event_loop()
  asyncio.set_event_loop(el)

  print("----- Running test '%s'" % (entry,))
  el.run_until_complete(locals()[entry]())
  print('----- Done')

  el.stop()
  el.close()
  
