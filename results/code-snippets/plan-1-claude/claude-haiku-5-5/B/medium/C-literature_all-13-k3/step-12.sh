
cd <SANDBOX_TMP>/tmp.dJiUhyh28T && cat << 'EOF' > fit2.py
exec(open('scan.py').read().split('best=None')[0].replace('print(groups((715,1000,4000)))',''))
def res(p):
    vals,mult=groups(p)
    if len(vals)!=4 or list(mult)!=[3,3,1,3]:
        return np.array([1e4,1e4,1e4])
    return vals[1:]-vals[0]-obs
for x0 in [(715,800,3000),(700,1000,4000),(800,900,3500)]:
    s=least_squares(res,x0,bounds=([300,300,1000],[1500,1600,7000]),x_scale=[50,50,300])
    print(s.x.round(1), s.fun.round(2), groups(s.x))
EOF
python3 fit2.py 2>&1 | tail -6
