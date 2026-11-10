src=open('fit2.py').read()
src=src.replace("t2=[e for e,n in g if n==3][0]","t2=[e-e0 for e,n in g if n==3][0]").replace("t1=[e for e,n in g if n==3][1:]","t1=[e-e0 for e,n in g if n==3][1:]")
open('fit2.py','w').write(src)
