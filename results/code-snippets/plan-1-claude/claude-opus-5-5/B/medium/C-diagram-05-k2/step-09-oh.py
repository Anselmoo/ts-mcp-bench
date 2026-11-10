import numpy as np, json
z=np.load('<SANDBOX_TMP>/H.npz'); Hee,Hcf,S2,ML=[z[k] for k in ('Hee','Hcf','S2','ML')]
B=859.
ph=np.exp(-1j*np.pi/2*ML)
par={('4','A2'):['F'],('4','T1'):['F','P'],('4','T2'):['F'],
('2','A1'):['G'],('2','A2'):['F'],('2','E'):['G','H','D','D'],('2','T1'):['G','H','P','F'],('2','T2'):['G','H','D','F','D']}
def levels(dq):
    H=Hee+dq*B*Hcf
    w,v=np.linalg.eigh(H); out=[]; i=0
    while i<len(w):
        j=i
        while j<len(w) and w[j]-w[i]<1e-6*B: j+=1
        P=v[:,i:j]; n=j-i
        s=np.trace(P.T@S2@P)/n; S=(np.sqrt(1+4*s)-1)/2; mult=int(round(2*S+1))
        dim=n//mult; chi=np.real(np.sum(np.abs(P)**2*ph[:,None]))/mult
        lab={1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}[dim][int(round(chi))]
        out.append([w[i],str(mult),lab]); i=j
    return out
res=[];allc={}
for dq in np.arange(0,4.01,0.5):
    d=dq if dq>0 else 1e-7
    L=levels(d); cnt={}; lv=[]
    for e,m,lab in L:
        k=(m,lab); c=cnt.get(k,0); cnt[k]=c+1
        lv.append([e,m+lab+'g',par[k][c] if len(par[k])>1 else '',m+lab+'g'+(f'({par[k][c]})' if len(set(par[k]))>1 else '')])
    if dq==0:
        Ef=np.linalg.eigvalsh(Hee)
    g=lv[0][0]
    lv=[[ (x[0]-g)/B if dq>0 else None ,x[3]] for x in lv]
    res.append((dq,lv))
# dq=0 exact energies: round
out=[]
for dq,lv in res:
    if dq==0:
        # use tiny dq energies rounded
        L=levels(1e-7); g=L[0][0]
        for i,x in enumerate(lv): x[0]=round((L[i][0]-g)/B,4)
    out.append({'dq_over_b':float(dq),'levels':[{'term':t,'e_over_b':round(e,4)} for e,t in lv[:6]]})
    print(dq,[(t,round(e,3)) for e,t in lv[:8]])
json.dump(out,open('<SANDBOX_TMP>/out.json','w'))
