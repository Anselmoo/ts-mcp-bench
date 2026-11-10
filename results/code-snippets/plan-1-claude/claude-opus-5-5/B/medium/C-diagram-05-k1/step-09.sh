cd $TMPDIR && python3 -c "
exec(open('ts.py').read())
Lp=np.zeros((N,N))
for i,(m,s) in enumerate(so):
    if m<2: Lp[so.index((m+1,s)),i]=np.sqrt(6-m*(m+1))
LpM=onebody(Lp); L2=LpM.T@LpM+np.diag(ML**2+ML)
H=H2+1e-3*B*HV
sel=np.where(np.isclose(MS,0.5))[0]
w,v=np.linalg.eigh(H[np.ix_(sel,sel)])
ph=np.exp(1j*np.pi/2*ML[sel])
for k in range(len(w)):
  e=(w[k])/B
  print(round(e,5), round(v[:,k]@L2[np.ix_(sel,sel)]@v[:,k],3), round((v[:,k].conj()*ph*v[:,k]).sum().real,2))
" | head -60 | tail -35