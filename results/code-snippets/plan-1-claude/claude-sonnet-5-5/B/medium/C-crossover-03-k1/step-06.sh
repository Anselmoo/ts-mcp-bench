cd <SANDBOX_TMP> && cat >> b.py <<'E'
E
sed -i '/^for D in/,$d' a.py && cat >> a.py <<'E'
for S in (0,1,2):
    sel=v[:,abs(w-S*(S+1))<1e-6];print(S,sel.shape[1],np.round(np.unique(np.round(np.linalg.eigvalsh(sel.T@HV@sel),0)),0)[:6])
E
python3 a.py