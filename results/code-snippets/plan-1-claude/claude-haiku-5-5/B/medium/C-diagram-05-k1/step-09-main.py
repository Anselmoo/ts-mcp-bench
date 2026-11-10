import numpy as np, ts, json, sys
Bv = 859.0; Cv = 3660.0
Cr = Cv/Bv
# Racah: B = (9F2-5F4)/441, C = 35F4/441  (calibrated: 15B for 4P-4F; integer d2/d7 relations)
F4 = 441*Cr/35.0
F2 = (441.0 + 5*F4)/9.0          # in units of B (B=1)
Hee, _ = ts.op_two_body(F2, F4)
U = {}
U_list = []
for (cs, ax, th) in ts.ROT:
    D5 = ts.Drot(ax, th)
    U_list.append(ts.Umany(D5))
# sectors (full 120-dim isometries)
nup = np.array([sum((b>>p)&1 for p in range(0,10,2)) for b in ts.basis])
q_idx = np.where(nup==5)[0]   # M_S = 3/2 : quartets only
d_idx = np.where(nup==4)[0]   # M_S = 1/2 : quartets + doublets
Vq = np.zeros((ts.N,len(q_idx)),dtype=complex)
for k,i in enumerate(q_idx): Vq[i,k]=1
# quartet lowering from M=3/2 to M=1/2 and doublet complement
Sm = np.zeros((ts.N,ts.N))
for j,bj in enumerate(ts.basis):
    for m in range(5):
        s1,b1 = ts.ann(2*m,bj)
        if s1==0: continue
        s2,b2 = ts.cre(2*m+1,b1)
        if s2==0: continue
        Sm[ts.idx[b2],j] += s1*s2
Qv = Sm[np.ix_(d_idx,q_idx)]
uu,ss,_ = np.linalg.svd(Qv)
Qb = uu[:,:len(q_idx)]
Pn = np.eye(len(d_idx)) - Qb@Qb.conj().T
u2,s2,_ = np.linalg.svd(Pn)
Pd = u2[:,:40]
Vd = np.zeros((ts.N,40),dtype=complex)
Vd[d_idx,:] = Pd
# L^2
Lz = np.zeros((5,5),dtype=complex); Lp=np.zeros((5,5),dtype=complex)
for mi,m in enumerate(ts.ms):
    Lz[mi,mi]=m
    if m<2: Lp[mi+1,mi]=np.sqrt(6-m*(m+1))
LZ = ts.op_one_body(ts.so_from_orb(Lz)); LP = ts.op_one_body(ts.so_from_orb(Lp))
L2 = LZ@LZ + 0.5*(LP@LP.conj().T + LP.conj().T@LP)
Lmap = {0:'S',1:'P',2:'D',3:'F',4:'G',5:'H'}
def Lfromval(x):
    L = int(round((-1+np.sqrt(1+4*x.real))/2))
    return Lmap[L]
CLS = ts.CLS_SIZE
GAMMA_ORDER = ['A1','A2','E','T1','T2']
def levels_for(Dq):
    Hcf = np.zeros((ts.N,ts.N),dtype=complex)
    h = ts.Hcf_orb(Dq)
    Hcf = ts.op_one_body(ts.so_from_orb(h))
    H = Hee + Hcf
    # check symmetry commutation with rotations
    err = max(np.abs(Ul@H - H@Ul).max() for Ul in U_list)
    out = {}
    for lab,Vs in (('q',Vq),('d',Vd)):
        Hs = Vs.conj().T@H@Vs
        Hs = (Hs+Hs.conj().T)/2
        w,V = np.linalg.eigh(Hs)
        Ls = Vs.conj().T@L2@Vs
        Us = [Vs.conj().T@Ul@Vs for Ul in U_list]
        # clusters
        clusters=[]
        i=0
        while i<len(w):
            j=i
            while j+1<len(w) and abs(w[j+1]-w[i])<1e-7: j+=1
            clusters.append((w[i:j+1].mean(), V[:,i:j+1]))
            i=j+1
        res=[]
        for E,Vc in clusters:
            chi=[]
            for k,Us_ in enumerate(Us):
                chi.append(np.trace(Vc.conj().T@Us_@Vc))
            dec = ts.decompose(chi)
            Lval = (Vc.conj().T@Ls@Vc)
            Lexp = np.trace(Lval).real/Vc.shape[1]
            for g,n in dec.items():
                for _ in range(n):
                    res.append((E, g, Lfromval(Lexp) if np.allclose(Lval, Lval[0,0]*np.eye(len(Lval)), atol=1e-6) or True else '?', lab))
        out[lab]=res
    return out, err
def fmt_gamma(g):
    return {'A1':'A1','A2':'A2','E':'E','T1':'T1','T2':'T2'}[g]
if __name__=='__main__':
    # calibrate parent labels at tiny Dq
    cal,_ = levels_for(1e-5)
    mapping={}
    for sec,mult in (('q',4),('d',2)):
        byG={}
        for E,g,Lf,_ in cal[sec]:
            byG.setdefault(g,[]).append((E,Lf))
        for g,lst in byG.items():
            lst.sort()
            mapping[(sec,g)] = [x[1] for x in lst]
    print(json.dumps({f'{k[0]}_{k[1]}':v for k,v in mapping.items()}))
    grid = [0.5*i for i in range(9)]
    results=[]
    for x in grid:
        out, err = levels_for(x)
        allL=[]
        for sec,mult in (('q',4),('d',2)):
            byG={}
            for E,g,Lf,_ in out[sec]:
                byG.setdefault(g,[]).append(E)
            for g,lst in byG.items():
                lst.sort()
                pars = mapping[(sec,g)]
                assert len(pars)==len(lst), (sec,g,len(pars),len(lst))
                cnt={}
                for r,E in enumerate(lst):
                    P = pars[r]
                    cnt[P]=cnt.get(P,0)+1
                for r,E in enumerate(lst):
                    P = pars[r]
                    allL.append((E, f"{mult}{g[0]}{g[1:] if False else ''}", sec,g,P))
        allL.sort(key=lambda t:t[0])
        E0 = allL[0][0]
        six=[]
        for E,_,sec,g,P in allL[:6]:
            mult = 4 if sec=='q' else 2
            gl = g[0]+g[1:]+('g' if True else '')
            six.append((str(mult)+ {'A1':'A1g','A2':'A2g','E':'Eg','T1':'T1g','T2':'T2g'}[g]+'('+P+')', (E-E0)))
        results.append((x, six, err))
        print(x, [(t, round(e,6)) for t,e in six], 'maxerr', err)
    json.dump([(x,[(t,e) for t,e in six]) for x,six,_ in results], open('results.json','w'), indent=1)
