s=open('run_d6.py').read()
s=s.replace("""                n=sum(csize[cc]*chi_cls[cc].real*ch[cc] for cc in range(5))/24
                if n>0.5: dec[name]=int(round(n))
            assert sum(dims[k]*n for k,n in dec.items())==len(c), (dec,len(c))""",
"""                n=sum(csize[cc]*chi_cls[cc].real*ch[cc] for cc in range(5))/24/(2*S+1)
                if n>0.5: dec[name]=int(round(n))
            assert sum(dims[k]*n for k,n in dec.items())*(2*S+1)==len(c), (dec,len(c))""")
open('run_d6.py','w').write(s)
