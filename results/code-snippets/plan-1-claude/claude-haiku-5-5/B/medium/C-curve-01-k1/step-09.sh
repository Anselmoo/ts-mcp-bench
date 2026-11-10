cat >> dbg.py <<'EOF'
H=Hee+ 738.9*Hcf
sel=np.abs(np.linalg.eigvalsh(S2)-6)<1e-6
w,v=np.linalg.eigh(S2); V=v[:,np.abs(w-6)<1e-6]
HS=V.conj().T@H@V; ev,evec=np.linalg.eigh(HS); Wall=V@evec
for i in range(3):
    W=Wall[:,i:i+1]
print('ev quintet', np.round(ev[:12]-ev[0],3))
Wg=Wall[:,np.abs(ev-ev[0])<1e-5]
for k,U in ops.items(): print(k, np.round(np.trace(Wg.conj().T@U@Wg),3))
print('dim quintet',V.shape)
for k,U in ops.items(): print('full in S=2', k, np.round(np.trace(V.conj().T@U@V),3))
EOF
python3 dbg.py | tail -12