SELECT s.id,s.ts,s.dur,s.name FROM slice s JOIN thread_track t ON s.track_id=t.id JOIN thread th ON t.utid=th.utid WHERE th.name='SurfaceFlinger' ORDER BY s.ts,s.id LIMIT 10001;
