"""PPUの実参照位置を照合した修正版の証拠を保存する。"""
import hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_ppu_layout'
CASES=(
 'movestress_detinput_captureburst_fixedmap_ppubase_v2_tracepalette',
 'movestress_detinput_fixedmap_ppubase_v2_tracepalette',
 'bossmovestress_detinput_fixedmap_ppubase_v2_tracepalette',
 'flipfixture_fixedmap_ppubase_v2_tracepalette',
)

def main():
 DEST.mkdir(parents=True,exist_ok=True)
 snapshot=BUILD/'fixedmap_ppubase_v2_build';snapshot.mkdir(exist_ok=True)
 for name in ('MonoSHSA1_4bpp_game.sfc','game.lbl','game.map','manifest.json',
              'ppu_sa1.bin','fixed_map_layout.json','native_near_packing.json','native_far_packing.json'):
  shutil.copyfile(BUILD/name,snapshot/name)
 cases=[]
 for name in CASES:
  d=BUILD/name;s=json.loads((d/'summary.json').read_text())
  assert s['pixelMatchedPresents']>=120 and not (d/'failure.txt').exists()
  states=list(d.glob('present*_ppu.json'))
  assert len(states)==s['pixelMatchedPresents']
  for p in states:
   q=json.loads(p.read_text())
   assert q['bg1Map']==q['bg2Map']==0xc000 and q['bg2Chr']==0xa000
   assert q['bg1Chr'] in (0,0x6000)
  s['hardwarePpuReferencesVerified']=True
  (d/'summary.json').write_text(json.dumps(s,indent=2)+'\n')
  cases.append(dict(scenario=name,**{k:s[k] for k in (
   'fields','logic','presents','pixelMatchedPresents','romSha256',
   'hardwarePpuReferencesVerified','presentationFieldIntervals','goal60fpsAchieved')}))
 archive=DEST/'evidence.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in (*CASES,snapshot.name):
   for p in sorted((BUILD/name).iterdir()):
    if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None
 report=dict(cases=cases,goal60fpsAchieved=False,hardwarePpuReferencesVerified=True,
  evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
 (DEST/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
 m=json.loads((BUILD/'manifest.json').read_text())
 assert all(c['romSha256']==m['romSha256'] for c in cases)
 m.update(stage='fixed-map-two-pages-ppu-aligned',goal60fpsAchieved=False,
          hardwarePpuReferencesVerified=True,validation=str(DEST.relative_to(ROOT)/'comparison.json').replace('\\','/'))
 shutil.copyfile(BUILD/'MonoSHSA1_4bpp_game.sfc',ROOT/'releases/MonoSHSA1_4bpp_experimental.sfc')
 (ROOT/'releases/sa1_4bpp_experimental.json').write_text(json.dumps(m,indent=2)+'\n')
 print(dict(cases=len(cases),archiveBytes=archive.stat().st_size,sha256=report['evidenceSha256']))

if __name__=='__main__':main()
