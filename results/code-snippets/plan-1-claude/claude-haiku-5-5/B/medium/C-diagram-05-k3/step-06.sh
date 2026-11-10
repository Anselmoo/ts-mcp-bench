cd <SANDBOX_TMP>/ts && python3 -c "
exec(open('ts.py').read())
ok=True
for i in range(24):
  for j in range(24):
    R = els[j]@els[i]
    k = [t for t in range(24) if np.allclose(els[t],R)][0]
    if not np.allclose(Us[i]@Us[j], Us[k]): ok=False
print('anti-hom ok', ok)
# Dq=0 check: quartet levels
Q = np.where(np.isclose(np.diag(Sz),1.5))[0]
print('quartet sector size', len(Q))
Hq = Hee[np.ix_(Q,Q)]
print('quartet Dq=0 energies', np.round(np.linalg.eigvalsh(Hq),6))
"