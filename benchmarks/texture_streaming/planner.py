"""Atomic logical-byte LRU plan; no physical residency or asynchronous claims."""
from collections import OrderedDict
class Planner:
 def __init__(self,sizes,capacity,upload_budget):
  if not sizes or any(type(k)!=str or not k or type(v)!=int or v<=0 for k,v in sizes.items()):raise ValueError('invalid sizes')
  if type(capacity)!=int or type(upload_budget)!=int or min(capacity,upload_budget)<=0:raise ValueError('invalid budget')
  self.sizes=dict(sizes);self.capacity=capacity;self.upload_budget=upload_budget;self.resident=OrderedDict();self.generation=0
 def plan(self,requests):
  if not isinstance(requests,list) or any(type(k)!=str or k not in self.sizes for k in requests):raise ValueError('unknown request')
  wanted=list(dict.fromkeys(requests));miss=[k for k in wanted if k not in self.resident]
  uploads=sum(self.sizes[k] for k in miss)
  if uploads>self.upload_budget:raise ValueError('upload budget exceeded')
  if sum(self.sizes[k] for k in wanted)>self.capacity:raise ValueError('working set exceeds capacity')
  next_state=self.resident.copy();evict=[]
  for k in miss:
   while sum(next_state.values())+self.sizes[k]>self.capacity:
    victim=next((v for v in next_state if v not in wanted),None)
    if victim is None:raise ValueError('no safe eviction')
    evict.append(victim);del next_state[victim]
   next_state[k]=self.sizes[k]
  for k in wanted:next_state.move_to_end(k)
  return dict(generation=self.generation,requests=list(requests),upload=miss,evict=evict,upload_bytes=uploads,resident_bytes=sum(next_state.values()),resident=list(next_state))
 def commit(self,plan):
  if plan!=self.plan(plan.get('requests')):raise ValueError('stale or modified plan')
  self.resident=OrderedDict((k,self.sizes[k]) for k in plan['resident']);self.generation+=1
