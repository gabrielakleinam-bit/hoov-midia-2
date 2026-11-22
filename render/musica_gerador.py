# Trilha original gerada por código (sem amostras externas). Uso: musica_gerador.py seed bpm key dur out.wav
# Origem: claude/hoov-musica-gerador.py do Projeto HOOV (10/11/2026). Custo: zero crédito.
import numpy as np, sys, wave
from scipy.signal import butter, lfilter
seed=int(sys.argv[1]); bpm=float(sys.argv[2]); key=sys.argv[3]; dur=float(sys.argv[4]); out=sys.argv[5]
rng=np.random.default_rng(seed); SR=44100; N=int(SR*dur)
L=np.zeros(N); R=np.zeros(N)
beat=60/bpm; s16=beat/4
NOTES={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
root=NOTES[key]
f=lambda midi: 440*2**((midi-69)/12)
def lp(x,fc,o=2): b,a=butter(o,fc/(SR/2)); return lfilter(b,a,x)
def hp(x,fc,o=2): b,a=butter(o,fc/(SR/2),'high'); return lfilter(b,a,x)
def bp(x,lo,hi): b,a=butter(2,[lo/(SR/2),hi/(SR/2)],'band'); return lfilter(b,a,x)
def add(sig,t,gain=1.0,pan=0.0):
    i=int(t*SR);
    if i>=N: return
    n=min(len(sig),N-i); l=gain*np.sqrt((1-pan)/2); r=gain*np.sqrt((1+pan)/2)
    L[i:i+n]+=sig[:n]*l; R[i:i+n]+=sig[:n]*r
def env(n,a,d):
    t=np.arange(n)/SR; e=np.exp(-t/d); k=int(a*SR);
    if k>0: e[:k]*=np.linspace(0,1,k)
    return e
def kick():
    n=int(.42*SR); t=np.arange(n)/SR; fr=48+110*np.exp(-t/0.035); ph=2*np.pi*np.cumsum(fr)/SR
    return np.tanh(2.2*np.sin(ph)*np.exp(-t/0.16))*0.9
def clap():
    n=int(.25*SR); x=rng.standard_normal(n); x=bp(x,900,5200); e=np.zeros(n)
    for o in (0,.011,.022): k=int(o*SR); e[k:]+=np.exp(-np.arange(n-k)/SR/0.05)
    return x*e*0.55
def hat(open_=False):
    n=int((.22 if open_ else .05)*SR); x=hp(rng.standard_normal(n),7500); return x*env(n,0,.09 if open_ else .018)*0.3
def bass(midi,d):
    n=int(d*SR); t=np.arange(n)/SR; fr=f(midi); x=2*((t*fr)%1)-1; x+=0.6*np.sin(2*np.pi*fr/2*t)
    return lp(x,380)*env(n,.004,d*0.9)*0.55
def pluck(midi,d):
    n=int(d*SR); t=np.arange(n)/SR; fr=f(midi); x=sum((1/h)*np.sin(2*np.pi*fr*h*t+rng.random()) for h in (1,2,3,4,5))
    return lp(x,2600)*env(n,.003,.22)*0.16
def mallet(midi,d=.35):
    n=int(d*SR); t=np.arange(n)/SR; fr=f(midi)
    x=np.sin(2*np.pi*fr*t)+0.35*np.sin(2*np.pi*fr*4*t)*np.exp(-t/0.03)
    return x*env(n,.002,.16)*0.32
# progressão menor: i - VI - III - VII (graus em semitons a partir da tônica)
prog=[(0,[0,3,7]),(8,[8,12,15]),(3,[3,7,10]),(10,[10,14,17])]
base=48+root  # C3 + key
bars=int(np.ceil(dur/(beat*4)))
# padrões variáveis pela seed
kpat=[[1,0,0,0, 0,0,1,0, 1,0,0,0, 0,0,0,0],[1,0,0,1, 0,0,1,0, 0,0,1,0, 0,0,0,0],[1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0]][seed%3]
bpat=[[1,0,0,1, 0,0,1,0, 0,0,1,0, 1,0,0,0],[1,0,1,0, 0,1,0,0, 1,0,0,1, 0,0,1,0]][seed%2]
hook=[rng.choice([0,3,5,7,10,12,15]) for _ in range(8)]
hpos=[0,3,6,8,10,11,13,14]
for bar in range(bars):
    t0=bar*4*beat; r,ch=prog[bar%4]
    for s in range(16):
        t=t0+s*s16
        if t>=dur-0.05: break
        if kpat[s]: add(kick(),t,1.0)
        if s in (4,12): add(clap(),t,0.9,0.1)
        if s%2==1 or rng.random()<0.25: add(hat(s%4==2 and rng.random()<0.3),t,0.7+0.3*rng.random(),-0.3)
        if bpat[s]: add(bass(base-12+r+(12 if s==10 and seed%2 else 0),s16*2.2),t,1.0)
        if s in (0,6,10) and bar>=0:
            for k,iv in enumerate(ch): add(pluck(base+12+iv,0.5),t+0.004*k,1.0,(k-1)*0.5)
    if bar>=1:
        for p,dg in zip(hpos,hook):
            t=t0+p*s16
            if t<dur-0.3: add(mallet(base+24+dg+r*0),t,1.0,0.25)
# final: impacto + cauda
tend=dur-0.9
fin=np.zeros(int(0.9*SR)); add(kick(),tend,1.1);
for k,iv in enumerate(prog[0][1]): add(pluck(base+12+iv,0.9),tend+0.01*k,1.3)
fade=np.ones(N); m=int(0.5*SR); fade[-m:]=np.linspace(1,0,m)**2; L*=fade; R*=fade
st=np.stack([L,R],1); st=np.tanh(st*1.3); st/=np.max(np.abs(st))+1e-9; st*=0.85
w=wave.open(out,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st*32767).astype('<i2').tobytes()); w.close()
print('ok',out,bpm,key,seed)
