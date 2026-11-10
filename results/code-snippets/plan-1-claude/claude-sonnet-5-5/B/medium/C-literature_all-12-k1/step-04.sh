cd /dev/shm; cat >> a.py <<'E'
print([(round(x),n) for x,n in lev(0,1000,4000)])
E
python3 a.py | tail -1