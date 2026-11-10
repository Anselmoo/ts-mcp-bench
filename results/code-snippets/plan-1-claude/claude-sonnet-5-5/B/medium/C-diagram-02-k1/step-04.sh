cat >> a.py <<'E'
print(abs(Hee-Hee.T).max(), np.round(np.linalg.eigvalsh(Hee)[:10]/B,2))
print(ck[2].round(3))
E
python3 a.py 2>&1 | tail -8