s=open('d4.py').read()
s=s.replace("def akval(k,a,b,cc,d):\n    s=0","def akval(k,a,b,cc,d):\n    a,b,cc,d=ms[a],ms[b],ms[cc],ms[d]\n    s=0")
s=s.replace("g1=integ(np.conj(Yd[a])*np.conj(Y(k,q,TH,PH))*Yd[cc])","g1=integ(np.conj(Yd[a])*np.conj(Y(k,q,TH,PH))*Yd[cc])")
open('d4.py','w').write(s)
