import functools
import asyncio
import random
from multi_await import MultiAwait
from multi_await import multi_await

async def raise_exception():
  int('z')

async def return_value():
  return 1

async def sleep_random():
  await asyncio.sleep(0.1 + random.random())
  return 'sleep'
  
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
    assert failures[1] == None
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
    assert failures[0] == None
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
  
