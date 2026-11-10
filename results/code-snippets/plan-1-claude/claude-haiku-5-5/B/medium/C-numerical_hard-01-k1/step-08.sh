python3 - <<'EOF'
s=open('d4.py').read()
s=s.replace("real_orb = [s15/2*X*Y, s15/2*X*Z, s15/2*Y*Z, s15/4*(X**2-Y**2), s5/4*(3*Z**2-1)]",
"real_orb = [s15/2*X*Y, s15/2*X*Z, s15/2*Y*Z, s15/4*(X**2-Y**2), s5/4*(3*Z**2-1)]\nreal_orb = [f/np.sqrt(np.sum(W*f*f)) for f in real_orb]")
s=s.replace("T = np.zeros((5,5,5,5))","T = np.zeros((5,5,5,5),dtype=complex)")
s=s.replace("ang[k]=T.real","ang[k]=T")
s=s.replace("A2,A4 = ang[2], ang[4]","A2,A4 = ang[2].real, ang[4].real\nprint('imag max', np.abs(ang[2].imag).max(), np.abs(ang[4].imag).max())")
open('d4.py','w').write(s)
EOF
python3 -c "
import d4,numpy as np
st,H,S2=d4.build(0.0)
print(H.shape, np.allclose(H,H.T), np.allclose(S2,S2.T))
ev,evec=np.linalg.eigh(H)
Sv = np.einsum('ij,ik,kj->j', evec, S2, evec)
import collections
d=collections.defaultdict(list)
for e,s in zip(ev,Sv): d[round(s,3)].append(round(e,4))
for s in d: print('S(S+1)=',s, sorted(set(d[s])))
"