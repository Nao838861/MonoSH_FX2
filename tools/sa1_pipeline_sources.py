"""既存の逐次描画を保存し、pipeline用のDMA排他と独立IRQ経路を生成する。"""

def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

def prepare(name,text,direct=False):
    if direct:text=direct_source(name,text)
    if name=='cpu':
        a=text.index('; SA-1の線形4bpp出力');b=text.index('wait_blank:',a)
        return text[:a]+'.include "pipeline_cpu.inc"\n'+text[b:]
    if name not in ('renderer','fast','near','edge'):return text
    text='.import sa1_dma_begin: far, sa1_dma_end: far\n'+text
    if name=='renderer':
        text='.import sa1_snapshot: far, sa1_dma_poll: far\n.export sa1_output_done\n'+text
        text=replace(text,'wait_job:\n  rep #$30', 'wait_job:\n  jsl sa1_dma_poll\n  rep #$30')
        text=replace(text,'wait_release:\n  lda $0100', 'wait_release:\n  jsl sa1_dma_poll\n  lda $1e\n  bne released_by_dma\n  lda $0100')
        text=replace(text,'  stz $0104\n  jmp wait_job', 'released_by_dma:\n  stz $1e\n  stz $0104\n  jmp wait_job')
        text=replace(text,'  rep #$30\nnext:', '  rep #$30\n  jmp next\n.segment "BOOT"\nnext:')
        text=replace(text,'  stz dy\nrow:', '  stz dy\n  jmp row\n.segment "SA1"\nrow:')
        text=replace(text,'  sep #$20\n  lda #$84\n  sta $2230\n  rep #$30\n  stz bgrow', '  rep #$30\n  stz bgrow')
        text=replace(text,'clear_scanline:\n', 'clear_scanline:\n  jsl sa1_dma_begin\n  sep #$20\n  lda #$84\n  sta $2230\n  rep #$20\n')
        text=replace(text,'  sta $2237\n  rep #$20\n  lda bgdest\n  clc\n  adc #128', '  sta $2237\n  jsl sa1_dma_end\n  rep #$20\n  lda bgdest\n  clc\n  adc #128')
        text=replace(text,'  sta bgwidth\n  lda bgscroll', '  sta bgwidth\n  jsl sa1_dma_begin\n  sep #$20\n  lda #$84\n  sta $2230\n  rep #$20\n  lda bgscroll')
        text=replace(text,'bg_far_next:\n', 'bg_far_next:\n  jsl sa1_dma_end\n')
        text=replace(text,'  jeq invoke_row\n  sep #$20', '  jeq invoke_row\n  jsl sa1_dma_begin\n  sep #$20')
        text=replace(text,'  rep #$20\n  lda codelen\n  sec\n  sbc #4', '  rep #$20\n  jsl sa1_dma_end\n  lda codelen\n  sec\n  sbc #4')
        text=replace(text,'  jsl sa1_prepare_transfer\n  sep #$20\n  lda #$b1\n  sta $2230\n  rep #$20', '  jsl sa1_prepare_transfer\n  jsl sa1_snapshot\nsa1_output_done:\n  rep #$20')
        text=text.replace('.assert * <= $0600','.assert * <= $05c0')
        if direct:text=text.replace('  jsl sa1_snapshot\n','')
    elif name=='fast':
        text=replace(text,'fast_base_ready:\n', 'fast_base_ready:\n  jmp fast_chunks\n')
        text=text.replace('cmp #21','cmp #9').replace('lda #20','lda #8')
        text=replace(text,'  sta fbytes\n  sta $2238', '  sta fbytes\n  jsl sa1_dma_begin\n  sta $2238')
        text=replace(text,'  rep #$20\n  ldx fbytes', '  rep #$20\n  jsl sa1_dma_end\n  ldx fbytes')
    elif name=='near':
        text=replace(text,'  jeq near_advance\n  sta $2238', '  jeq near_advance\n  jsl sa1_dma_begin\n  sta $2238')
        text=replace(text,'  rep #$20\n  ldx nlength', '  rep #$20\n  jsl sa1_dma_end\n  ldx nlength')
    elif name=='edge':
        text=replace(text,'edge_save_line:\n', 'edge_save_line:\n  jsl sa1_dma_begin\n')
        text=replace(text,'  sta $2235\n  jsr edge_next', '  sta $2235\n  jsl sa1_dma_end\n  jsr edge_next')
        text=replace(text,'edge_restore_line:\n', 'edge_restore_line:\n  jsl sa1_dma_begin\n')
        text=replace(text,'  sta $2237\n  rep #$20\n  jsr edge_next', '  sta $2237\n  jsl sa1_dma_end\n  rep #$20\n  jsr edge_next')
    return '.setcpu "65816"\n'+text


def direct_source(name,text):
    if name in ('renderer','fast','near','edge'):
        text=text.replace('lda #$40','lda $0102')
    if name=='renderer':
        text='.import sa1_fb_read: far, sa1_fb_write: far\n'+text
        text=replace(text,'sa1_clear_start:\n', 'sa1_clear_start:\n  stz $10\n  lda $0102\n  sta $12\n')
        text=text.replace('lda f:$400000,x','jsl sa1_fb_read').replace('sta f:$400000,x','jsl sa1_fb_write')
        text=replace(text,'  jsl sa1_prepare_transfer\n', '  jsl sa1_prepare_transfer\n')
    if name=='dirty':
        text=replace(text,'dirty_return:\n  rtl', 'dirty_return:\n  ldx #0\npipeline_merge:\n  lda $0120,x\n  tay\n  cmp f:$430400,x\n  bcc :+\n  lda f:$430400,x\n:\n  sta $0120,x\n  tya\n  sta f:$430400,x\n  lda $0122,x\n  tay\n  cmp f:$430402,x\n  bcs :+\n  lda f:$430402,x\n:\n  sta $0122,x\n  tya\n  sta f:$430402,x\n  inx\n  inx\n  inx\n  inx\n  cpx #96\n  bne pipeline_merge\n  rtl')
        a=text.index('transfer_row:\n');b=text.index('  lda dirty_right\n',a)
        text=text[:a]+'transfer_row:\n  lda $0120,x\n  sta dirty_left\n  lda $0122,x\n  sta dirty_right\n'+text[b:]
    return text
