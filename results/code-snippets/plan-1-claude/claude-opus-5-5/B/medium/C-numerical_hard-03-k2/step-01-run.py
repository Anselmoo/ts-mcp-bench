exec(open('/tmp/d5.py').read())
def doublets(Dq,B):
    w,s=levels(Dq,B,4.6*B)
    # group degenerate levels
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        S=s[i]; out.append((w[i],j-i,round(S,2))); i=j
    return out
lv=doublets(2500,600)
print(lv[:10])
