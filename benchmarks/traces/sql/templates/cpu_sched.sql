SELECT s.id,s.ts,s.dur,s.cpu FROM sched s JOIN thread th ON s.utid=th.utid WHERE th.name='RenderThread' ORDER BY s.ts,s.id LIMIT 10001;
