"""C参照版と65816版を同じ入力・更新回数で比較し、状態と描画矩形を保存する。"""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from build_game import BUILD, GAME

TOOLS=Path(__file__).resolve().parent

def reference_cache_fingerprint():
    # GSU描画だけの改修時に参照を再利用する。ロジック・入力・ABI変更では拒否。
    files=[p for p in GAME.iterdir() if p.suffix in {'.c','.h','.s','.inc','.lua','.json'}
           and not p.name.startswith('gsu')]
    files+=list((GAME/'upstream').rglob('*'))+list((GAME/'platform').rglob('*'))
    files+=[TOOLS/'build_game.py']
    digest=hashlib.sha256()
    for p in sorted(set(p for p in files if p.is_file())):
        digest.update(str(p.relative_to(GAME.parent.parent)).encode())
        digest.update(p.read_bytes())
    return digest.hexdigest()

def run(name,*args):
    subprocess.run([sys.executable,'-X','utf8',str(TOOLS/name),*map(str,args)],check=True)

def capture(reference=False):
    run('build_game.py',*(['--reference-logic'] if reference else []))
    rom_sha=hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
    captures={}
    for scenario,frames in [('equivalence',8000),('equivalence_boss',4000)]:
        run('test_game.py','--scenario',scenario,'--frames',frames,'--timeout',180)
        states=(BUILD/scenario/'states.bin').read_bytes()
        raw=json.loads((BUILD/scenario/'state_blocks.json').read_text())
        saved=BUILD/(scenario+('_reference' if reference else '_native'))
        saved.mkdir(exist_ok=True)
        (saved/'states.bin').write_bytes(states)
        (saved/'state_blocks.json').write_text(json.dumps(raw)+'\n')
        (saved/'rom.sha256').write_text(rom_sha+'\n')
        (saved/'logic.sha256').write_text(reference_cache_fingerprint()+'\n')
        blocks=[(raw[str(i)]['1'],raw[str(i)]['2']) for i in range(1,len(raw)+1)]
        captures[scenario]=(states,blocks)
    return rom_sha,captures

def main():
    if '--reuse-reference' in sys.argv:
        ref_cases={}; reference=None
        for scenario in ['equivalence','equivalence_boss']:
            saved=BUILD/(scenario+'_reference')
            assert (saved/'logic.sha256').read_text().strip()==reference_cache_fingerprint(), 'reference logic/input cache changed'
            sha=(saved/'rom.sha256').read_text().strip()
            assert reference is None or reference==sha
            reference=sha
            raw=json.loads((saved/'state_blocks.json').read_text())
            blocks=[(raw[str(i)]['1'],raw[str(i)]['2']) for i in range(1,len(raw)+1)]
            ref_cases[scenario]=((saved/'states.bin').read_bytes(),blocks)
    else:
        reference,ref_cases=capture(True)
    native,native_cases=capture()
    for scenario in ref_cases:
        compare(scenario,reference,native,ref_cases[scenario],native_cases[scenario])

def compare(scenario,reference,native,ref_capture,native_capture):
    a,blocks=ref_capture
    b,native_blocks=native_capture
    assert blocks==native_blocks
    stride=sum(size for _,size in blocks)
    n=min(len(a),len(b))//stride
    assert n >= (3500 if scenario=='equivalence' else 1000),n
    boss_states=set()
    for frame in range(n):
        offset=frame*stride
        count=0
        for name,size in blocks:
            aa=a[offset:offset+size];bb=b[offset:offset+size]
            if name=='_fx_draw_count':count=aa[0]
            if name=='_monosh_boss_state':boss_states.add(aa[0])
            if name=='_fx_draw':aa=aa[:count*10];bb=bb[:count*10]
            assert aa==bb,f'update {frame+1}, {name}: {aa.hex()} != {bb.hex()}'
            offset+=size
    if scenario=='equivalence_boss': assert {1,2,3} <= boss_states,boss_states
    results=GAME/'results'/scenario;results.mkdir(exist_ok=True)
    for name,states in [('reference',a),('native',b)]:
        (results/(name+'.bin.gz')).write_bytes(gzip.compress(states,mtime=0))
    report={'referenceRomSha256':reference,'nativeRomSha256':native,'matchedUpdates':n,
            'recordBytes':stride,'referenceUpdates':len(a)//stride,'nativeUpdates':len(b)//stride,
            'blocks':blocks,'bossStates':sorted(boss_states),
            'input':'96更新ごとに右・左・上・下・右上・左下・中立・中立、連射を保持',
            'comparison':'全状態ブロックは全byte、描画矩形はdrawCountの有効要素を比較'}
    (results/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(scenario,'C/native exact state and active draw match:',n,'updates')

if __name__=='__main__':main()
