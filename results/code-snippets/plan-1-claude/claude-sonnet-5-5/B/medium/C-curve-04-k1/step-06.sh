cd <SANDBOX_TMP>; sed -i 's/for x in (1.45,2.55,3.25):/for x in (0,1.45,2.55,3.25):/' a.py; python3 a.py | head -1; python3 - <<'E'
exec(open('<SANDBOX_TMP>/a.py').read().split('for x in (0')[0])
print(np.abs(Hee-Hee.T).max(), np.abs(H1-H1.T).max(), np.abs(Hee@S2-S2@Hee).max(), np.trace(S2)/n)
E