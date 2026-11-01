SELECT c.id,c.ts,c.value,t.name,t.unit FROM counter c JOIN counter_track t ON c.track_id=t.id WHERE t.name='gles.gpu_frequency_mhz' ORDER BY c.ts,c.id LIMIT 10001;
