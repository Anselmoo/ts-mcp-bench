src=open('d3.py').read()
src=src.replace("l=list(d); l[l.index(a)]=x; l[l.index(b)]=y","l=list(d); ia=d.index(a); ib=d.index(b); l[ia]=x; l[ib]=y")
open('d3.py','w').write(src)
