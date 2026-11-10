import re
s=open('run_d6.py').read()
s=s.replace("""def classify(R):
    tr=np.trace(R).real
    if abs(tr-3)<1e-6: return 0
    if abs(tr)<1e-6: return 1
    if abs(tr-1)<1e-6: return 2
    if abs(tr+1)<1e-6:
        return 3 if np.all(np.abs(np.diag(R))>1e-6) else 4
classes=[classify(R) for R,_ in G24]""","""def classify_all():
    keys=list(els.keys())
    c4=[k for k in keys if abs(np.trace(els[k][0]).real-1)<1e-6]
    c4sq=set(k3(els[k][0]@els[k][0]) for k in c4)
    cls=[]
    for k in keys:
        tr=np.trace(els[k][0]).real
        if abs(tr-3)<1e-6: cls.append(0)
        elif abs(tr)<1e-6: cls.append(1)
        elif abs(tr-1)<1e-6: cls.append(2)
        else: cls.append(3 if k in c4sq else 4)
    return cls
classes=classify_all()""")
open('run_d6.py','w').write(s)
