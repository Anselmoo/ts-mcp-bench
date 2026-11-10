s=open('a.py').read()
s=s.replace("float((-1)**a*5*gaunt(2,k,2,-a,a-cc,cc))","float((-1)**a*gaunt(2,k,2,-a,a-cc,cc))*np.sqrt(4*np.pi/(2*k+1))")
s=s.replace("Fk={2:F2/49,4:F4/441}","Fk={2:F2,4:F4}")
open('a.py','w').write(s)
