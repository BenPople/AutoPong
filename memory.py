import gc, os

def free_disk():
  s = os.statvfs('//')
  return ('{0}MB disk space free'.format((s[0]*s[3])/1048576))

def free_memory(full=False):
  gc.collect()

  free = gc.mem_free()
  allocated = gc.mem_alloc()
  total = free + allocated

  percentage = '{0:.2f}%'.format((free/total) * 100)

  if not full: return percentage
  else: return ('Total:{0}KB Free:{1}KB ({2})'.format(total, free, percentage))