"""Part B reference generation and hierarchical prediction. No gate data is trained on."""
import os
os.environ.setdefault('OMP_NUM_THREADS','4')
from pathlib import Path
import concurrent.futures,csv,itertools,json,re,subprocess,tempfile,time
import numpy as np
import joblib
from generate_data import ROOT,PARAMS,BLOCKS,nominal
from train_models import features

def devices(gate):
    # name, kind, drain, gate, source, body; fixed Wn=90nm Wp=180nm.
    inv=lambda inp,out,tag:[(tag+'p','pmos',out,inp,'vdd','vdd'),(tag+'n','nmos',out,inp,'0','0')]
    if gate=='INV':return inv('a','out','i')
    dest='mid' if gate in ['AND2','OR2'] else 'out'
    if gate in ['NAND2','AND2']:
        d=[('p1','pmos',dest,'a','vdd','vdd'),('p2','pmos',dest,'b','vdd','vdd'),('n1','nmos',dest,'a','x','0'),('n2','nmos','x','b','0','0')]
    else:
        d=[('p1','pmos','x','a','vdd','vdd'),('p2','pmos',dest,'b','x','vdd'),('n1','nmos',dest,'a','0','0'),('n2','nmos',dest,'b','0','0')]
    return d+(inv('mid','out','i') if dest=='mid' else [])

def reference(job):
    gate,bits,ci,c=job;dd=devices(gate)
    text='* Part B '+gate+' '+bits+'\n'
    for kind in ['nmos','pmos']:
        b=BLOCKS[kind]
        for p in PARAMS:b=re.sub(r'(\b'+p+r'\s*=\s*)[^\s]+',lambda m:m[1]+format(c[kind][p],'.17g'),b,flags=re.I)
        text+=b+'\n'
    text+=f'.options gmin=1e-18 abstol=1e-18 reltol=1e-6 vntol=1e-9\n.temp {c["temp"]:.17g}\nVDD vdd 0 {c["vdd"]:.17g}\n'
    for node,bit in zip('ab',bits):text+=f'V{node} {node} 0 {int(bit)*c["vdd"]:.17g}\n'
    for name,kind,d,g,s,b in dd:text+=f'M{name} {d} {g} {s} {b} {kind} L=45n W={180e-9 if kind=="pmos" else 90e-9:.17g}\n'
    nodes=sorted({n for dev in dd for n in dev[2:]}-{'0'})
    vectors=[f'v({n})' for n in nodes]+['i(vdd)']+[f'i(v{n})' for n in 'ab'[:len(bits)]]
    text+='.control\nset numdgt=17\nop\n'+'\n'.join('print '+v for v in vectors)+'\nquit\n.endc\n.end\n'
    with tempfile.TemporaryDirectory(prefix='triode_gate_') as td:
        path=Path(td)/'gate.cir';path.write_text(text);r=subprocess.run(['ngspice','-b',str(path)],capture_output=True,text=True,timeout=20)
    log=r.stdout+r.stderr
    if r.returncode:raise RuntimeError(log)
    vals={}
    for vec in vectors:
        m=re.search(re.escape(vec)+r'\s*=\s*([-+0-9.eE]+)',log,re.I)
        if not m:raise RuntimeError(log)
        vals[vec]=float(m[1])
    volts={n:vals['v('+n+')'] for n in nodes};volts['0']=0.
    # Total rail-equivalent static current, including high logic-input sources.
    leakage=-vals['i(vdd)']-sum(int(bit)*vals['i(v'+n+')'] for n,bit in zip('ab',bits))
    supply=-vals['i(vdd)']
    result=dict(gate=gate,bits=bits,corner=ci,spice_leakage=leakage,spice_vdd_current=supply,voltages=volts,conditions=c)
    if ci==0:(ROOT/'gates'/f'{gate}_{bits}.cir').write_text(text)
    return result

def predict(result,models):
    c=result['conditions'];volts=result['voltages'];positive={'vdd'}|{n for n,b in zip('ab',result['bits']) if b=='1'}
    dd=devices(result['gate'])
    parent={n:n for dev in dd for n in dev[2:]}
    def find(n):
        while parent[n]!=n:n=parent[n]
        return n
    for name,kind,d,g,source,body in dd:
        high=volts[g]>c['vdd']/2
        if (high if kind=='nmos' else not high):parent[find(d)]=find(source)
    highroot=find('vdd')
    if highroot==find('0'):raise ValueError('Conducting VDD-to-ground path')
    total=0.;supply=0.
    for name,kind,d,g,s,b in dd:
        high=volts[g]>c['vdd']/2;on=high if kind=='nmos' else not high;case=kind+('_on' if on else '_off')
        row=dict(vdd=c['vdd'],temp=c['temp'],w=180e-9 if kind=='pmos' else 90e-9,vd=volts[d],vs=volts[s],**c[kind])
        x=features({k:np.array([v]) for k,v in row.items()});bundle=models[case]
        cache=models.get('_predictions')
        currents=cache[(result['gate'],result['bits'],result['corner'],name)] if cache is not None else (bundle['model'].predict(x)[0] if bundle.get('output')=='physical_signed_current' else np.sinh(np.clip(bundle['model'].predict(x)[0],-100,100))*bundle['scale'])
        # Apply KCL at the boundary of the conducting high-rail component.
        # When both diffusion terminals lie inside, their sum is -Ig-Ib;
        # this avoids predicting tiny Vds conduction by subtracting large currents.
        di=find(d)==highroot;si=find(s)==highroot
        if di and si: supply-=currents[1]+currents[3]
        else:supply+=di*currents[0]+si*currents[2]
        if g not in ['a','b'] and find(g)==highroot:supply+=currents[1]
        if find(b)==highroot:supply+=currents[3]
        if g in positive and g in ['a','b']:total+=currents[1]
    total+=supply
    return total,supply

def main():
    out=ROOT/'gates';out.mkdir(exist_ok=True);rng=np.random.default_rng(20261210);corners=[]
    for i in range(200):corners.append(dict(vdd=float(rng.uniform(.9,1.1)),temp=float(rng.uniform(-40,125)),**{k:{p:nominal(k)[p]*float(rng.uniform(.9,1.1)) for p in PARAMS} for k in ['nmos','pmos']}))
    (out/'corners.json').write_text(json.dumps(corners,indent=2))
    jobs=[(g,''.join(bits),i,c) for g in ['INV','NAND2','NOR2','AND2','OR2'] for bits in itertools.product('01',repeat=1 if g=='INV' else 2) for i,c in enumerate(corners)]
    if (out/'reference.json').exists() and (out/'seed_20261210.json').exists():
        results=json.loads((out/'reference.json').read_text())
    else:
        results=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            for r in pool.map(reference,jobs):
                results.append(r)
                if len(results)%200==0:print('Gate references',len(results),'/ 3600',flush=True)
        (out/'reference.json').write_text(json.dumps(results))
        (out/'seed_20261210.json').write_text(json.dumps({'seed':20261210}))
    print('Gate reference complete; awaiting four selected models.',flush=True)
    cases=['nmos_on','nmos_off','pmos_on','pmos_off']
    while not all((ROOT/'ml'/(c+'.joblib')).exists() for c in cases):time.sleep(10)
    models={c:joblib.load(ROOT/'ml'/(c+'.joblib')) for c in cases};rows=[]
    for r in results:
        ml,supply=predict(r,models);rows.append(dict(gate=r['gate'],bits=r['bits'],corner=r['corner'],spice=r['spice_leakage'],ml=ml,spice_vdd=r['spice_vdd_current'],ml_vdd=supply,output_voltage=r['voltages']['out']))
    with (out/'predictions.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary=[]
    for gate,bits in dict.fromkeys((r['gate'],r['bits']) for r in rows):
        rr=[r for r in rows if r['gate']==gate and r['bits']==bits];y=np.array([r['spice'] for r in rr]);p=np.array([r['ml'] for r in rr]);e=100*abs(y-p)/np.maximum(abs(y),1e-18)
        summary.append(dict(gate=gate,bits=bits,spice_median_A=float(np.median(y)),ml_median_A=float(np.median(p)),bias_A=float(np.mean(p-y)),median_error_percent=float(np.median(e)),p95_error_percent=float(np.percentile(e,95))))
    (out/'metrics.json').write_text(json.dumps(summary,indent=2));print('Part B baseline predictions complete',flush=True)

if __name__=='__main__':main()
