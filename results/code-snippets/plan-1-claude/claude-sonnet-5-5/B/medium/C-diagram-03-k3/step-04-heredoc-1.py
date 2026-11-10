s=open('t.py').read()
s=s.replace("U=np.array([coef(f) for f in fs]);U=","nr=[np.linalg.norm(coef(f)) for f in fs]\nfs=[(lambda f,n:(lambda x,y,z:f(x,y,z)/n))(f,n) for f,n in zip(fs,nr)]\nU=np.array([coef(f) for f in fs]);U=")
open('t.py','w').write(s)
