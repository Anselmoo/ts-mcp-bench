cd $TMPDIR && python3 -c "
exec(open('ts.py').read())
Lp=np.zeros((N,N))
for i,(m,s) in enumerate(so):
    if m<2: Lp[so.index((m+1,s)),i]=np.sqrt(6-m*(m+1))
LpM=onebody(Lp); L2=LpM.T@LpM+np.diag(ML**2+ML)
H=H2+1e-4*B*HV
sel=np.where(np.isclose(MS,0.5))[0]
w,v=np.linalg.eigh(H[np.ix_(sel,sel)])
for k in range(len(w)):
  e=(w[k]-w[0])/B
  if 4.9<e<5.1: print(round(e,6), round(v[:,k]@L2[np.ix_(sel,sel)]@v[:,k],3), ML[sel][np.argmax(abs(v[:,k]))])
"