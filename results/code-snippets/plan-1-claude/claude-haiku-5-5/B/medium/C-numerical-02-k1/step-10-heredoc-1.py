import re
s=open('run.py').read()
s=s.replace("""    H=Hmat(Dq,F0,F2,F4).real
    w,v=np.linalg.eigh(H)
    S=np.real(np.einsum('in,ij,jn->n',v,S2op,v))
    return w,S""","""    H=Hmat(Dq,F0,F2,F4).real
    w,v=np.linalg.eigh(H+50.0*S2op)
    S=np.real(np.einsum('in,ij,jn->n',v,S2op,v))
    E=np.real(np.einsum('in,ij,jn->n',v,H,v))
    return E,S""")
open('run.py','w').write(s)
