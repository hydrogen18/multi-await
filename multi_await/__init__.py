import contextlib
import asyncio

@contextlib.asynccontextmanager
async def multi_await():
  ma = MultiAwait()
  try:
    yield ma
  finally:
    await ma.cancel() 

class MultiAwait(object):
  def __init__(self):
    self.tasks = []
    self.srcs = []
    self.completed = []
    
  def add(self, src):
    # Add to list of sources
    self.srcs.append(src)
    # Add to list of tasks that are 'complete', which need to be started again
    self.completed.append(len(self.srcs) - 1)
    # Add a blank slot for the task
    self.tasks.append(None)

  async def cancel(self): 
    for t in self.tasks:
      if t is None:
        continue               
      t.cancel()            
      try:
        await t        
      except asyncio.CancelledError as e:
        pass
      
    # [t.cancel() for t in self.tasks if t is not None]
    self.tasks = [None for _ in self.srcs] # leave in a good state
    self.completed.clear()
    
  async def get(self):       
    if len(self.srcs) == 0:
      raise RuntimeError('Attempted to await 0 coroutines')
       
    # Fill in any blank tasks
    for i in self.completed:
      src = self.srcs[i]
      coro_or_task = src()
      if isinstance(coro_or_task, asyncio.Task):
        task = coro_or_task
      else:
        task = asyncio.create_task(coro_or_task)
      self.tasks[i] = task
    self.completed.clear()
        
    try:
      done, pending = await asyncio.wait(self.tasks, return_when = asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError as e:
      self.cancel()
      raise e
     
    results = []
    failures = []

    for i, task in enumerate(self.tasks):     
      if task in done:
        # Record this task as done, so it is started again
        self.completed.append(i)

        self.tasks[i] = None
        task_result = None
        try:
          task_result = task.result()        
        except Exception as failure:
          failures.append(failure)
          results.append(None)  
        else:
          failures.append(None)
          results.append(task_result)       
      else:
        results.append(None)
        failures.append(None)     

    return (results, failures,)

