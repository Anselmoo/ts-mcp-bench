
cd /tmp/tsbench-run-9aa2jt5t; cat >> b.py <<'E'
w=np.linalg.eigvalsh(H(d2,0));e6=np.linalg.eigvalsh(H(d6,0))[0]
print(sorted(set(np.round(w-e6,0)))[:12], 10*B+5*C)
E
python3 b.py 0 | tail -1