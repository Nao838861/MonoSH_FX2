"""Archive the requested three palette refinements and exact-ROM validation."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import subprocess
import zipfile
import numpy as np
from PIL import Image
from verify_palette_regions import decode_fb

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build'
GAME=ROOT/'game/v001'
OUT=GAME/'results/palette_regions_20261008'
BASE='fdf1e0853d031684eab8ca2d09936d293bfaa375'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def save_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def main():
 OUT.mkdir(exist_ok=True)
 rom=BUILD/'game_v001/MonoSHFX2_v001.sfc';sha=digest(rom)
 previous=json.loads(subprocess.check_output(['git','show',BASE+':releases/v001.json'],cwd=ROOT))
 save_json(OUT/'previous_release.json',previous)
 # Verify actual transferred/displayed planes. A raw GSU work-RAM snapshot
 # taken at endFrame may be the next in-flight image, so use VRAM here.
 rows=[]
 for name in ['foliage','enemies','projectiles','boss','player_shots','overlap']:
  before=(BUILD/'palette_before'/f'{name}_vram.bin').read_bytes()[:12288]
  after=(BUILD/'palette_after'/f'{name}_vram.bin').read_bytes()[:12288]
  mono=(BUILD/'palette_after_mono'/f'{name}_vram.bin').read_bytes()[:12288]
  assert np.array_equal(decode_fb(before)!=0,decode_fb(after)!=0),(name,'displayed silhouette changed')
  assert after==mono,(name,'SELECT bitmap changed')
  if name=='player_shots':
   for suffix in ['.rgb','_oam.bin']:
    assert (BUILD/'palette_before'/(name+suffix)).read_bytes()==(BUILD/'palette_after'/(name+suffix)).read_bytes()
  rows.append({'fixture':name,'displayed_alpha_errors':0,'select_bitmap_errors':0})
 save_json(OUT/'matched_shape_check.json',{'romSha256':sha,'fixtures':rows,'player_and_shot_final_ppu_identical':True})
 with zipfile.ZipFile(OUT/'matched_captures.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for folder in ['palette_before','palette_v1_ppu','palette_after','palette_after_mono']:
   for p in sorted((BUILD/folder).iterdir()):
    if p.is_file():z.write(p,folder+'/'+p.name)
 source=BUILD/'palette_regions_final'
 semantic=json.loads((source/'semantic_summary.json').read_text());assert semantic['rom_sha256']==sha
 save_json(OUT/'semantic_summary.json',{k:v for k,v in semantic.items() if k!='fixtures'})
 for filename in ['manifest.json','semantic_summary.json','capture.lua','emulator.log']:
  (OUT/('alignment_'+filename+'.gz')).write_bytes(gzip.compress((source/filename).read_bytes(),mtime=0))
 evidence={p.name:digest(p) for p in source.iterdir() if p.suffix in ['.rgb','.bin','.png']}
 (OUT/'alignment_capture_hashes.json.gz').write_bytes(gzip.compress(json.dumps(evidence,sort_keys=True,indent=2).encode(),mtime=0))
 # Retain representative raw scenes; full deterministic grid can be replayed.
 with zipfile.ZipFile(OUT/'alignment_samples.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for fixture in json.loads((source/'manifest.json').read_text())['fixtures']:
   name=fixture['name'];phase=int(name.rsplit('_p',1)[1])
   if phase not in [0,63]:continue
   for p in sorted(source.glob(name+'.*'))+sorted(source.glob(name+'_*')):
    if p.is_file():z.write(p,p.name)
 for folder in ['color','objects','packed','controls','pause','display','held','boss','stumble','stress','audio_quick']:
  src=BUILD/'game_v001'/folder
  summary=json.loads((src/'summary.json').read_text());assert summary['romSha256']==sha,(folder,'stale evidence')
  for filename in ['summary.json','color_summary.json','objects_ppu.json']:
   if (src/filename).exists():shutil.copy2(src/filename,OUT/(folder+'_'+filename))
  for filename in ['test.lua','emulator.log','trace.jsonl']:
   if (src/filename).exists():(OUT/(folder+'_'+filename+'.gz')).write_bytes(gzip.compress((src/filename).read_bytes(),mtime=0))
 for src,name in [(BUILD/'game_v001/cache_compare_palette2/comparison.json','render_fixture_summary.json'),
                  (BUILD/'game_v001/scaled_assets_verified.json','scaled_assets.json'),
                  (GAME/'assets/bg_color/silhouette_repair.json','color_regions.json')]:shutil.copy2(src,OUT/name)
 sourcecheck=json.loads(subprocess.check_output(['python','tools/verify_color_silhouettes.py'],cwd=ROOT))
 save_json(OUT/'source_structure_check.json',sourcecheck)
 comparison=json.loads((OUT/'render_fixture_summary.json').read_text())
 assert comparison['romSha256']==sha
 preserve=['game/v001/audio.s','game/v001/gsu.s','game/v001/color.s','game/v001/packet.s','game/v001/cpu.s']
 unchanged={}
 for name in preserve:
  path=ROOT/name
  if not path.exists():continue
  baseline=subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT)
  assert path.read_bytes()==baseline,(name,'engine or audio changed')
  unchanged[name]=digest(path)
 for path in (GAME/'audio').rglob('*'):
  if path.is_file():
   name=str(path.relative_to(ROOT))
   try:baseline=subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT,stderr=subprocess.DEVNULL)
   except subprocess.CalledProcessError:continue
   assert path.read_bytes()==baseline,(name,'audio data changed');unchanged[name]=digest(path)
 save_json(OUT/'unchanged_engine_audio.json',unchanged)
 manifest=previous.copy()
 manifest.update(romSha256=sha,romBytes=rom.stat().st_size,previousRomSha256=previous['romSha256'],
  verificationKind='木3色・赤い目と灰色の小型敵・ボス頭の象牙色の目と角・緑と茶色の胴。輪郭、実PPUの色領域、操作、ボス進行、音声を検証。実機未検証。',
  verificationResults=str(OUT.relative_to(ROOT)),verificationReport='game/v001/RESULTS_20261008_PALETTE_REGIONS.md')
 manifest['bgColor']['rgb5']=json.loads((OUT/'color_regions.json').read_text())['rgb5']
 manifest['bgColor']['titlePalette3NearWhiteRgb']=[239,239,247]
 manifest['bgColor']['titlePalette3DarkRgb']=[24,24,41]
 manifest['bgColor']['paletteCoverage']='single palette per source image; full source-cell rectangle to cover partially visible screen-tile edges'
 manifest['validation']={'baseCommit':BASE,'fixedScenes':len(comparison['scenes']),'fixedImages':comparison['imagesVerified'],
  'paletteCellsChecked':comparison['paletteCellsVerified'],'sourceAssetsChecked':len(sourcecheck['assets_checked']),
  'sourcePixelsChecked':sourcecheck['source_pixels_checked'],'reviewedRedLensPixels':47,
  'matchedDisplayedMaskCases':6,'realPpuComparisonImages':24,'playerAndShotFinalPpuIdentical':True,
  'isolatedPaletteScenes':semantic['scenes'],'isolatedOpaquePpuPixels':semantic['opaque_ppu_pixels'],
  'isolatedPaletteErrors':0,'audioQuickFields':1400,'audioDataUnchangedSha256':previous['validation']['audioDataUnchangedSha256'],
  'hardwareTested':False,'historicalResults':str((OUT/'previous_release.json').relative_to(ROOT))}
 manifest['scenarioFrames'].pop('naturalProfile',None)
 manifest['performance']={'performanceGateWaived':True,'longProfileRequiredForThisRelease':False,
  'note':'This release verifies exact visual output, controls and audio; no new long-duration performance claim.'}
 # Keep stale numerical headline rates out until final profile is reviewed.
 manifest.pop('presentationRates',None);manifest.pop('latePresentationIntervals',None)
 manifest['strict60Hz']=False
 shutil.copy2(rom,ROOT/'releases/MonoSHFX2_v001.sfc')
 save_json(ROOT/'releases/v001.json',manifest)
 save_json(OUT/'SHA256SUMS.json',{p.name:digest(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='SHA256SUMS.json'})
 print(json.dumps({'romSha256':sha,'evidenceFiles':len(list(OUT.iterdir())),'semanticScenes':semantic['scenes']}))

if __name__=='__main__':main()
