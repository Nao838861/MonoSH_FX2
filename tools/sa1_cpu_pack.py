"""S-CPU側で疎なタイルだけを変換し、WRAMに連続して保持する試験。"""
from sa1_dense import pipeline as dense_pipeline


def pipeline(text):
    text=dense_pipeline(text)
    text=text.replace('sbc #1300','sbc #1700').replace('sbc #2400','sbc #2800')
    text=text.replace('.include "pipeline_stage.inc"','.include "cpu_pack_stage.inc"')
    text=text.replace('jsr pipe_stage_convert','jsl $c10000+pipe_stage_convert')
    text=text.replace('  .ifdef SA1_STAGED\n  bra pipe_after_flip_reserve\n  .endif','')
    text=text.replace('  .ifdef SA1_STAGED\n  jmp pipe_irq_done\n  .else\n  lda pipe_presented_irq','  .ifdef SA1_STAGED\n  jsr pipe_flip\n  jmp pipe_choose_target\n  .else\n  lda pipe_presented_irq')
    return text


def transform(name,text):
    if name=='cpu':
        text=text.replace('.include "pipeline_cpu.inc"','.include "pipeline_dense.inc"')
    if name=='renderer':
        text='.setcpu "65816"\n.import sa1_sparse_map_prepare: far\n'+text
        old='  jsl sa1_transfer_mask_prepare\n  jsl sa1_deep_rebase'
        assert old in text
        text=text.replace(old,'  jsl sa1_transfer_mask_prepare\n  jsl sa1_sparse_map_prepare\n  jsl sa1_deep_rebase',1)
    if name=='transfer_mask':
        marker='\nsa1_transfer_mask_prepare:\n'
        assert text.count(marker)==1
        before,after=text.split(marker,1)
        after=after.replace('lda #65','lda #1',1).replace('f:$432900,x','f:$432800,x')
        text=before+marker+after
    return text
