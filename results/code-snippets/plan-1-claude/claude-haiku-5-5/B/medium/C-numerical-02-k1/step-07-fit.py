from run import *
def quartet_levels(Dq,F2,F4):
    w,S=levels(Dq,0.0,F2,F4)
    q=w[np.abs(S-3.75)<1e-6]
    # cluster distinct
    out=[]
    for e in np.sort(q):
        if not out or abs(e-out[-1][0])>1e-3: out.append([e,1])
        else: out[-1][1]+=1
    return out
# free-ion check: 4P-4F = 15B
w,S=levels(0,0,1.0,0.0)
q=quartet_levels(0,1.0,0.0); print("free quartet levels (F2=1,F4=0):",q)
# Racah B from Slater: compute B for F2=1,F4=0 and F4=1 and deduce
def free(F2,F4):
    q=quartet_levels(0,F2,F4); return q
print(free(1,0), free(0,1))
