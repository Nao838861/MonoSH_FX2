"""同じ入力・同じ論理フレーム区間で、音なし基準ROMと現行ROMを比較する。"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from build_game import ROOT, BUILD
from run_probe import prepare_runtime, MESEN_EXE, lua

SCRIPT = r'''
local labels=LABELS
local output=OUTDIR
local started=nil
local firstField=nil
local audioStart=nil
local times={}
local function read(name) return emu.read(0x7e0000+labels[name],emu.memType.snesMemory) end
local function frame() return emu.read16(0x7e0000+labels._monosh_runtime_frame_counter,emu.memType.snesMemory) end
emu.addEventCallback(function() emu.setInput({a=true},0) end,emu.eventType.inputPolled)
emu.addMemoryCallback(function()
 local n=frame()
 if n==100 then started=emu.getState().masterClock;firstField=emu.getState().frameCount end
 if n==2100 then
  local state=emu.getState()
  local elapsed=((state.masterClock-started)&0xffffffff)/21477272
  local f=assert(io.open(output..'/perf.json','w'))
  local sum=0;local max=0;for _,t in ipairs(times) do sum=sum+t;max=math.max(max,t) end
  f:write(string.format('{"logicFrames":2000,"seconds":%.9f,"fps":%.6f,"fields":%d,"audioMeanMs":%.9f,"audioMaxMs":%.9f}',elapsed,2000/elapsed,state.frameCount-firstField,#times>0 and sum/#times or 0,max));f:close()
  local b={}
  for _,item in ipairs({{'_monosh_player_x',2},{'_monosh_player_bottom',2},{'_monosh_player_state',1},
     {'_monosh_player_bullets',15},{'_monosh_reflected_bullets',15},{'_monosh_enemies',80},
     {'_monosh_boss_state',1},{'_monosh_boss_hp',1}}) do
   for i=0,item[2]-1 do b[#b+1]=string.char(emu.read(0x7e0000+labels[item[1]]+i,emu.memType.snesMemory)) end
  end
  f=assert(io.open(output..'/state.bin','wb'));f:write(table.concat(b));f:close();emu.stop(0)
 end
end,emu.callbackType.exec,0x7f0000+labels._fx_frame,0x7f0000+labels._fx_frame,emu.cpuType.snes,emu.memType.snesMemory)
if labels.fx_audio_process then
 emu.addMemoryCallback(function() audioStart=emu.getState().masterClock end,emu.callbackType.exec,labels.fx_audio_process,labels.fx_audio_process,emu.cpuType.snes,emu.memType.snesMemory)
 emu.addMemoryCallback(function()
   if started then times[#times+1]=((emu.getState().masterClock-audioStart)&0xffffffff)/21477.272 end
 end,emu.callbackType.exec,0x7f0000+labels.render_finished+4,0x7f0000+labels.render_finished+4,emu.cpuType.snes,emu.memType.snesMemory)
end
'''


def main():
    mesen = prepare_runtime(MESEN_EXE)
    settings = mesen.parent / 'settings.json'
    config = json.loads(settings.read_text())
    config['Snes']['Port1'] = {'Type': 'SnesController'}
    config['Debug']['ScriptWindow']['ScriptTimeout'] = 10
    settings.write_text(json.dumps(config))
    summaries = {}
    for name, rom, label_path in [
        ('baseline', ROOT / '.cache/tad/baseline.sfc', ROOT / '.cache/tad/baseline.lbl'),
        ('native', BUILD / 'MonoSHFX2_v001.sfc', BUILD / 'game.lbl')]:
        out = BUILD / ('audio_perf_' + name)
        out.mkdir(exist_ok=True)
        labels = {m[2]: int(m[1], 16) for m in re.finditer(r'al ([0-9A-Fa-f]+) \.([^\s]+)', label_path.read_text())}
        script = out / 'test.lua'
        script.write_text(SCRIPT.replace('LABELS', lua(labels)).replace('OUTDIR', lua(out.as_posix())))
        result = subprocess.run([str(mesen), '--testRunner', '--timeout=180', '--doNotSaveSettings',
            '--enableStdout', str(rom), str(script)], cwd=mesen.parent, capture_output=True,
            timeout=190, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (out / 'emulator.log').write_bytes(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        summary = json.loads((out / 'perf.json').read_text())
        summary.update(romSha256=hashlib.sha256(rom.read_bytes()).hexdigest(),
            stateSha256=hashlib.sha256((out / 'state.bin').read_bytes()).hexdigest())
        summaries[name] = summary
        print(name, summary, flush=True)
    assert summaries['baseline']['stateSha256'] == summaries['native']['stateSha256'], 'game progression changed'
    (BUILD / 'audio_perf.json').write_text(json.dumps(summaries, indent=2) + '\n')


if __name__ == '__main__':
    main()
