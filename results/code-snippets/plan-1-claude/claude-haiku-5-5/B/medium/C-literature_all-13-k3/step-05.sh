
cd <SANDBOX_TMP>/tmp.dJiUhyh28T && sed -i 's/from scipy.special import sph_harm/from scipy.special import sph_harm_y/; s/def Y(l,m,t,p): return sph_harm(m,l,p,t)/def Y(l,m,t,p): return sph_harm_y(l,m,t,p)/' d7.py && python3 d7.py
