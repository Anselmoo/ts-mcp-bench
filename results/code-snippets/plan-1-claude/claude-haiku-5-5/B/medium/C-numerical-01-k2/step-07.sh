cat >> fit.py << 'EOF'

def levels(Dq,B,C):
    e=spectrum(Dq,B,C); g=e.min()
    # collect distinct levels above ground with multiplicity
    out=[];
    for x in np.sort(e):
        if out and abs(x-out[-1][0])<1e-6: out[-1][1]+=1
        else: out.append([x,1])
    return [(round(x-g,3),m) for x,m in out]
def trans(Dq,B,C):
    lv=levels(Dq,B,C)
    T=[x for x,m in lv if m==3 and x>1e-6]
    return T
obs=np.array([20700,30570,42990.])
print(levels(1000,500,2250))
def res(p,fixC=None):
    Dq,B=p[0],p[1]; C=fixC if fixC is not None else p[2]
    T=trans(Dq,B,C)
    return np.array(T[:3])-obs
for lab,fc in [('C=4B',None)]:
    pass
# fit with C=4B
f=lambda p: res([p[0],p[1],4*p[1]])
s=least_squares(f,[2000,700],x_scale=[1000,300])
Dq,B=s.x; print("C=4B: Dq,B=",Dq,B, "resid",s.fun, "T:",trans(Dq,B,4*B))
# free C
s2=least_squares(lambda p: res(p),[2000,700,3000],x_scale=[1000,300,1000])
print("free C: Dq,B,C=",s2.x,"resid",s2.fun,"T:",trans(*s2.x))
EOF
python3 fit.py