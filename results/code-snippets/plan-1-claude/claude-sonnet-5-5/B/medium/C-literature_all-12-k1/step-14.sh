cd /dev/shm; cat > e.py <<'E'
exec(open('/dev/shm/d.py').read().split("def quart")[0]) if False else None
E
echo skip