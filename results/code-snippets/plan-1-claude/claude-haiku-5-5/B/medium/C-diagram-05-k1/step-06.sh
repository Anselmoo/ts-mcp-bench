cat > calib.py << 'EOF'
import numpy as np, ts
H2, g = ts.op_two_body(1.0,0.0)
H4, _ = ts.op_two_body(0.0,1.0)
# sector indices
nup = [sum(1 for p in range(0,10,2) if (b>>p)&1) for b in ts.basis]
q_idx = [i for i,n in enumerate(nup) if n==5]   # M_S=3/2
d_idx = [i for i,n in enumerate(nup) if n==4]   # M_S=1/2
# L operators
Lz = np.zeros((5,5),dtype=complex); Lp=np.zeros((5,5),dtype=complex)
for mi,m in enumerate(ts.ms):
    Lz[mi,mi]=m
    if m<2: Lp[mi+1,mi]=np.sqrt(6-m*(m+1))
LZ = ts.op_one_body(ts.so_from_orb(Lz)); LP = ts.op_one_body(ts.so_from_orb(Lp))
L2 = LZ@LZ + 0.5*(LP@LP.conj().T + LP.conj().T@LP)
# quartet block
def block(M, ids): return M[np.ix_(ids,ids)]
for name,H in (('F2',H2),('F4',H4)):
    Hq = block(H,q_idx)
    w = np.linalg.eigvalsh(Hq)
    print(name,'quartet eigen',np.round(w,6))
# quartet: 4F L=3 (L2=12), 4P L=1 (L2=2)
Lq = block(L2.real,q_idx)
print('L2 quartet', np.round(np.linalg.eigvalsh(Lq),6))
EOF
python3 calib.py