"""最新の敵弾描画とVRAM四面・費用表の組合せを保存する。"""
import hashlib,json,zipfile
from pathlib import Path
from report_sa1_compact_game import packets

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'
DEST=ROOT/'game/sa1/v001/results/20261010_four_shapes'
CASES=(
 'movestress_detinput_captureburst_fixedmap_resident_v1_tracepalette',
 'movestress_detinput_captureburst_fourshapes_v1_tracepalette',
 'movestress_detinput_captureburst_fourshapes_budget_v1_tracepalette',
 'movestress_detinput_captureburst_fourshapes_cputable_v1_tracepalette',
 'movestress_detinput_captureburst_fourshapes_sa1table_v1_tracepalette',
 'movestress_detinput_captureburst_fourshapes_partialtable_v1_tracepalette',
 'movestress_detinput_captureburst_cpupackshapes_v1_tracepalette',
)
FOLDERS=('fourshapes_v1_build','fourshapes_budget_v1_build','fourshapes_cputable_v1_build',
 'fourshapes_sa1table_v1_build','fourshapes_partialtable_v1_build','cpupackshapes_v1_build')


def main():
 DEST.mkdir(parents=True,exist_ok=True)
 reference=packets(CASES[0]);cases=[]
 for name in CASES:
  d=BUILD/name;s=json.loads((d/'summary.json').read_text())
  assert s['pixelMatchedPresents']>=168 and not (d/'failure.txt').exists()
  actual=packets(name);n=min(len(reference),len(actual));assert reference[:n]==actual[:n]
  e={k:s[k] for k in ('fields','logic','presents','pixelMatchedPresents','romSha256',
   'irqMathRegistersVerified','goal60fpsAchieved','presentationFieldIntervals')}
  e.update(scenario=name,logicMatchedGenerations=n,
   hardwarePpuReferencesVerified=False,displayVerificationComplete=False,
   firstVisibleField=s['presentationTimes'][0]['visibleField'],
   maxSa1Ms=max(x['totalSa1Ms'] for x in s['sa1Jobs']))
  jobs=[json.loads(x) for x in (d/'prefix_dma.jsonl').read_text().splitlines()] if (d/'prefix_dma.jsonl').exists() else []
  e['maxPrefixPlanMs']=max((x['planMs'] for x in jobs),default=0)
  cases.append(e)
 archive=DEST/'evidence.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in (*CASES,*FOLDERS):
   for p in sorted((BUILD/name).iterdir()):
    if p.is_file() and p.suffix!='.rgb':z.write(p,name+'/'+p.name)
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None
 report=dict(cases=cases,goal60fpsAchieved=False,adopted=False,
  displayVerificationComplete=False,
  limitation='Legacy tests decoded assumed VRAM addresses without checking actual PPU CHR/map bases. Fixed-map and four-page layouts were subsequently found invalid. These cases do not establish correct displayed images.',
  evidenceSha256=hashlib.sha256(archive.read_bytes()).hexdigest())
 (DEST/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
 print(dict(cases=len(cases),archiveBytes=archive.stat().st_size,sha256=report['evidenceSha256']))


if __name__=='__main__':main()
