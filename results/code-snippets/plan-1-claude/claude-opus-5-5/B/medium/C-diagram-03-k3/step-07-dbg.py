exec(open('ts.py').read().split('import json')[0])
for dq in [0,1e-5,1e-3,0.5]:
    w=np.linalg.eigvalsh(H2+H1*(dq+1e-5)*B); print(dq,np.round((w[:20]-w[0])/B,5))
