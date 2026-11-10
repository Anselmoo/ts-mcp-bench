from dbl import *
def t1_doublets(Dq,B,C):
    q,_=levels(Dq,B,C); g0=q[0]
    res=analyze(Dq,B,C)
    return [(round(e-g0,1),dg,tr.real) for e,dg,tr in res]
if __name__=="__main__":
    print(Dq,B)
    for x in t1_doublets(Dq,B,4*B)[:12]: print(x)
