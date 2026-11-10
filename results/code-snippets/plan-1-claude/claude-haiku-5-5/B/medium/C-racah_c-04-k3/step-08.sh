python3 - << 'EOF'
import re
src=open('d3.py').read()
src=src.replace("H1+=P[m,m2]*CD[2*m+s]@C[2*m2+s]","H1+=P[m,m2]*restrict(cd[2*m+s]@c[2*m2+s])")
src=src.replace("H2+=0.5*(Vc@F)*(CD[i]@CD[j]@C[l]@C[k])","H2+=0.5*(Vc@F)*restrict(cd[i]@cd[j]@c[l]@c[k])")
src=src.replace("def spin2():","def spin2_unused():")
src+='''
def spin2():
    Sz=[0.5*(cd[2*m]@c[2*m]-cd[2*m+1]@c[2*m+1]) for m in range(5)]
    Szt=sum(Sz)
    Sp=sum(cd[2*m]@c[2*m+1] for m in range(5))
    Sm=sum(cd[2*m+1]@c[2*m] for m in range(5))
    S2=Szt@Szt+0.5*(Sp@Sm+Sm@Sp)
    return restrict(S2)
'''
open('d3.py','w').write(src)
EOF
python3 -c "
import d3,numpy as np
H=d3.build_H(0,1.0,0.0)
print(np.allclose(H,H.conj().T))
ev=np.linalg.eigvalsh(H)
print(np.unique(np.round(ev,3),return_counts=True))
S2=d3.spin2().real
print(np.unique(np.round(np.linalg.eigvalsh(S2),3),return_counts=True))
"