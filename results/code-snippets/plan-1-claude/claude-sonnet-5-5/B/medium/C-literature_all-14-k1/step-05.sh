
cd /dev/shm
cat >> a.py <<'E'
ph=np.array([sum(-so[i][0] for i in range(10) if d>>i&1) for d in dets])
Dm=np.exp(1j*np.pi/2*ph)
def lv(Dq,B,Cc):
    w,v=np.linalg.eigh(build(Dq,B,Cc)); out=[];i=0
    while i<120:
        j=i
        while j<120 and abs(w[j]-w[i])<1e-5: j+=1
        V=v[:,i:j]; n=j-i
        S2=np.trace(V.T@S2M@V)/n; S=(-1+np.sqrt(1+4*S2))/2; mult=round(2*S+1)
        ch=np.trace(V.conj().T@(Dm[:,None]*V)).real
        spat=n//mult
        lab={1:'A1' if ch/mult>0 else 'A2',2:'E',3:'T1' if ch/mult>0 else 'T2'}[spat]
        out.append((w[i],mult,lab)); i=j
    return out
def pick(p):
    L=lv(*p); g=L[0][0]
    q=[e-g for e,m,l in L if m==4]
    t1=[e-g for e,m,l in L if m==2 and l=='T1']
    return q[1],q[3],t1[1]
print([(round(e-lv(900,900,3900)[0][0]),m,l) for e,m,l in lv(900,900,3900)[:12]])
print(pick((900,900,3900)))
r=least_squares(lambda p:np.array(pick(p))-np.array([8100,19400,21600]),[900,900,3900],x_scale=[100,100,300])
print(r.x,pick(r.x),r.cost)
for s in [(700,700,3000),(1000,1000,4500),(800,1100,2500),(1000,600,5000)]:
    r=least_squares(lambda p:np.array(pick(p))-np.array([8100,19400,21600]),s,x_scale=[100,100,300]);print(r.x,r.cost)
E
python3 a.py 2>&1 | tail -8
