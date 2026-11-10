def f(Dq):
    q=gs(Dq,4); t=gs(Dq,2)
    t=list(t)
    for e in q:
        j=min(range(len(t)),key=lambda i:abs(t[i]-e)); t.pop(j)
    return q[0]-min(t)
for D in (1000,2000,3000):print(D,f(D))
print(brentq(f,500,4000,xtol=0.01))
