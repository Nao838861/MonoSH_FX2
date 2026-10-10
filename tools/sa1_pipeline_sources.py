"""既存の逐次描画を保存し、pipeline用のDMA排他と独立IRQ経路を生成する。"""

def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

def prepare(name,text,direct=False,irq=False,transfer_tiles=False,merge_dma=False,padded=False,large_edge=False,triple_bw=False,cpu_copy=False,cpu_fill=False,cpu_far=False):
    if direct:text=direct_source(name,text)
    if triple_bw and name=='dirty':
        text=replace(text,'dirty_return:\n  ldx #0', 'dirty_return:\n  lda $0116\n  cmp #1\n  bne triple_initialized\n  ldx #0\ntriple_init_history:\n  lda #128\n  sta f:$430400,x\n  sta f:$430460,x\n  lda #0\n  sta f:$430402,x\n  sta f:$430462,x\n  inx\n  inx\n  inx\n  inx\n  cpx #96\n  bne triple_init_history\ntriple_initialized:\n  ldx #0')
        text=text.replace('  cmp #3\n  bcs dirty_return', '  cmp #4\n  bcs dirty_return').replace('  cmp #2\n  bcs dirty_return','  cmp #3\n  bcs dirty_return')
        text=replace(text,'  sta $0120,x\n  tya\n  sta f:$430400,x','  sta f:$4304c0,x\n  cmp f:$430460,x\n  bcc :+\n  lda f:$430460,x\n:\n  sta $0120,x\n  lda f:$430400,x\n  sta f:$430460,x\n  tya\n  sta f:$430400,x')
        text=replace(text,'  sta $0122,x\n  tya\n  sta f:$430402,x','  sta f:$4304c2,x\n  cmp f:$430462,x\n  bcs :+\n  lda f:$430462,x\n:\n  sta $0122,x\n  lda f:$430402,x\n  sta f:$430462,x\n  tya\n  sta f:$430402,x')
    if triple_bw and name=='dirty':
        text=replace(text,'transfer_row:\n  lda $0120,x\n  sta dirty_left\n  lda $0122,x\n  sta dirty_right', 'transfer_row:\n  lda f:$4304c0,x\n  sta dirty_left\n  lda f:$4304c2,x\n  sta dirty_right')
    if name=='cpu':
        if irq:
            text=text.replace('.import sa1_entry','.import sa1_entry, sa1_dma_irq')
            text=replace(text,'  lda #sa1_entry', '  lda #sa1_dma_irq\n  sta $2207\n  lda #sa1_entry')
        a=text.index('; SA-1の線形4bpp出力');b=text.index('wait_blank:',a)
        text=text[:a]+'.include "pipeline_cpu.inc"\n'+text[b:]
        if large_edge:text='SA1_CC_BUFFER = $02e0\n'+text
        return text
    if name=='dirty' and transfer_tiles:
        text=replace(text,'  jml sa1_tiles_transfer', '  jsl sa1_tiles_transfer\n  lda #$2000\n  sta $14\n  lda $011a\n  cmp #51\n  bcs transfer_band_fallback\n  rtl\ntransfer_band_fallback:\n  lda #$0800\n  sta $14')
    if name not in ('renderer','fast','near','edge'):return text
    text='.import sa1_dma_begin: far, sa1_dma_end: far\n'+text
    if name=='renderer':
        text='.import sa1_snapshot: far, sa1_dma_poll: far\n.export sa1_output_done, sa1_sprite_begin, sa1_sprite_done\n'+text
        text=replace(text,'\nnext:\n','\nnext:\nsa1_sprite_begin:\n')
        text=replace(text,'\nskip:\n','\nskip:\nsa1_sprite_done:\n')
        if irq:text=replace(text,'wait_job:\n', '  sep #$20\n  lda #$80\n  sta $220a\n  rep #$30\n  cli\nwait_job:\n')
        text=replace(text,'wait_job:\n  rep #$30', 'wait_job:\n  jsl sa1_dma_poll\n  rep #$30')
        text=replace(text,'wait_release:\n  lda $0100', 'wait_release:\n  jsl sa1_dma_poll\n  lda $1e\n  bne released_by_dma\n  lda $0100')
        text=replace(text,'  stz $0104\n  jmp wait_job', 'released_by_dma:\n  stz $1e\n  stz $0104\n  jmp wait_job')
        text=replace(text,'  rep #$30\nnext:', '  rep #$30\n  jmp next\n.segment "BOOT"\nnext:')
        text=replace(text,'  stz dy\nrow:', '  stz dy\n  jmp row\n.segment "SA1"\nrow:')
        text=replace(text,'  sep #$20\n  lda #$84\n  sta $2230\n  rep #$30\n  stz bgrow', '  rep #$30\n  stz bgrow')
        text=replace(text,'clear_scanline:\n', '  jsl sa1_dma_begin\n  sep #$20\n  lda #$84\n  sta $2230\n  rep #$20\nclear_scanline:\n')
        text=replace(text,'  sta $2237\n  rep #$20\n  lda bgdest\n  clc\n  adc #128', '  sta $2237\n  rep #$20\n  lda bgdest\n  clc\n  adc #128')
        # 空の帯では DMA を獲得していない。CPU に渡した grant を消さない。
        text=text.replace('  beq clear_tile_next', '  jeq clear_row_done').replace('  bmi clear_tile_next', '  jmi clear_row_done')
        text=replace(text,'clear_tile_next:\n','clear_tile_next:\n  jsl sa1_dma_end\nclear_row_done:\n')
        text=replace(text,'  sta bgwidth\n  lda bgscroll', '  sta bgwidth\n  jsl sa1_dma_begin\n  sep #$20\n  lda #$84\n  sta $2230\n  rep #$20\n  lda bgscroll')
        text=replace(text,'bg_far_next:\n', 'bg_far_next:\n  jsl sa1_dma_end\n')
        text=replace(text,'  jeq invoke_row\n  sep #$20', '  jeq invoke_row\n  jsl sa1_dma_begin\n  sep #$20')
        text=replace(text,'  rep #$20\n  lda codelen\n  sec\n  sbc #4', '  rep #$20\n  jsl sa1_dma_end\n  lda codelen\n  sec\n  sbc #4')
        text=replace(text,'  jsl sa1_prepare_transfer\n  sep #$20\n  lda #$b1\n  sta $2230\n  rep #$20', '  jsl sa1_prepare_transfer\n  jsl sa1_snapshot\nsa1_output_done:\n  rep #$20')
        if irq:text=replace(text,'  sta $0104\nwait_release:', '  sta $0104\n  sep #$20\n  lda #$80\n  sta $2209\n  rep #$20\nwait_release:')
        text=text.replace('.assert * <= $0600','.assert * <= $05c0')
        if direct:text=text.replace('  jsl sa1_snapshot\n','')
        if merge_dma:
            text='.import sa1_merge_dma: far\n'+text
            text=replace(text,'  jsl sa1_prepare_transfer\n','  jsl sa1_prepare_transfer\n  jsl sa1_merge_dma\n')
    elif name=='fast':
        if not irq:
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
    if cpu_fill and name=='renderer':
        text='.import sa1_cpu_clear_line: far\n'+text
        text=replace(text,'  jsl sa1_dma_begin\n  sep #$20\n  lda #$84\n  sta $2230\n  rep #$20\nclear_scanline:', 'clear_scanline:')
        text=replace(text,'clear_scanline:\n  lda bgfirst', 'clear_scanline:\n  lda $011e\n  bne clear_using_cpu\n  jsl sa1_dma_begin\n  sep #$20\n  lda #$84\n  sta $2230\n  rep #$20\n  lda bgfirst')
        text=replace(text,'  sta $2237\n  rep #$20\n  lda bgdest\n  clc\n  adc #128','  sta $2237\n  rep #$20\n  jsl sa1_dma_end\n  bra clear_cpu_advance\nclear_using_cpu:\n  jsl sa1_cpu_clear_line\nclear_cpu_advance:\n  lda bgdest\n  clc\n  adc #128')
        text=replace(text,'clear_tile_next:\n  jsl sa1_dma_end', 'clear_tile_next:')
    if cpu_far and name=='renderer':
        text='.import sa1_cpu_far_line: far\n'+text
        text=text.replace('  beq bg_far_next', '  jeq bg_far_next').replace('  bmi bg_far_next', '  jmi bg_far_next')
        text=replace(text,'  sta bgwidth\n  jsl sa1_dma_begin', '  sta bgwidth\n  lda $011e\n  beq bg_far_using_dma\n  jsl sa1_cpu_far_line\n  jmp bg_far_cpu_done\nbg_far_using_dma:\n  jsl sa1_dma_begin')
        text=replace(text,'bg_far_next:\n  jsl sa1_dma_end', 'bg_far_next:\n  jsl sa1_dma_end\nbg_far_cpu_done:')
    if cpu_copy:text=cpu_copy_source(name,text)
    if padded:text=padded_source(name,text)
    if large_edge:text=large_edge_source(name,text)
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


def ground_buffers(text,depth):
    if depth==3:return text
    text=replace(text,'  cmp #3\n','  cmp #'+str(depth)+'\n')
    text=replace(text,'sky_tables: .res 30','sky_tables: .res '+str(depth*10))
    text=replace(text,'ground_horizontal_keys: .res 6','ground_horizontal_keys: .res '+str(depth*2))
    text=replace(text,'sky_tables+20\n','sky_tables+20'+''.join(', sky_tables+'+str(i*10) for i in range(3,depth))+'\n')
    for table,label,size in [('color1_pointers','_fx_ground_color1',150),('color3_pointers','_fx_ground_color3',150),('horizontal_pointers','_fx_ground_horizontal',270),('far_pointers','_fx_ground_far_x',10)]:
        prefix=table+': .word '
        a=text.index(prefix);b=text.index('\n',a)
        text=text[:b]+''.join(', pipeline_'+table+'_'+str(i) for i in range(3,depth))+text[b:]
    text+='\n.segment "COLORBSS"\n.export pipe_ground_extra, pipe_ground_extra_end\npipe_ground_extra:\n'
    for i in range(3,depth):
        for table,size in [('color1_pointers',150),('color3_pointers',150),('horizontal_pointers',270),('far_pointers',10)]:
            text+='pipeline_'+table+'_'+str(i)+': .res '+str(size)+'\n'
    text+='pipe_ground_extra_end:\n'
    if depth>8:
        for name,size in [('sky_tables',depth*10),('ground_horizontal_keys',depth*2)]:
            text=replace(text,name+': .res '+str(size),'')
            text+=name+': .res '+str(size)+'\n'
    return text


def padded_source(name,text):
    if name=='renderer':
        text=text.replace('.repeat 7\n    asl','.repeat 8\n    asl')
        text=text.replace('.repeat 8\n    lsr','.repeat 9\n    lsr')
        text=text.replace('  adc #128\n  sta bgdest','  adc #256\n  sta bgdest')
        text=text.replace('  .endrepeat\n  sta rowbase','  .endrepeat\n  clc\n  adc #64\n  sta rowbase')
        text=text.replace('  .endrepeat\n  sta bgdest','  .endrepeat\n  clc\n  adc #64\n  sta bgdest')
        text=replace(text,'  lda bgrow\n  xba\n  asl\n  asl\n  clc\n  adc $0120,x', '  lda bgrow\n  xba\n  asl\n  asl\n  asl\n  clc\n  adc #64\n  clc\n  adc $0120,x')
        text=replace(text,'  lda $0120,x\n  sta dirtyL\n  lda $0122,x\n  sta dirtyR\n  cmp dirtyL', '  lda #0\n  sta dirtyL\n  lda #128\n  sta dirtyR\n  cmp dirtyL')
        text=replace(text,'  lda dirtyL\n  cmp $b4','  jmp row_partial\n  lda dirtyL\n  cmp $b4')
    elif name=='fast':
        text=replace(text,'  .repeat 7\n    asl', '  .repeat 8\n    asl')
        text=replace(text,'  adc $48\n  sta spriteBase', '  adc $48\n  clc\n  adc #64\n  sta spriteBase')
        text=replace(text,'  jsl sa1_edge_prepare', '  lda $c0\n  and #255\n  clc\n  adc $38\n  bpl padded_left_safe\n  cmp #$ff80\n  jcc fast_fail\npadded_left_safe:\n  lda $c2\n  and #255\n  clc\n  adc $38\n  bmi padded_x_safe\n  cmp #385\n  jcs fast_fail\npadded_x_safe:\n  stz $c4')
    return text


def large_edge_source(name,text):
    if name=='renderer':
        text=replace(text,'  jmp next\n.segment "BOOT"', '  jmp next\n.assert * <= $02e0, error, "SA1 worker overlaps CC buffer"\n.segment "BOOT"')
        text=replace(text,'.segment "SA1"\nrow:', '.segment "BOOT"\nrow:')
        text=text.replace('.assert * <= $0700, error, "SA-1 shared worker overlaps edge JIT"','')
        text=text.replace('.assert * <= $05c0, error, "SA-1 worker overlaps guard cache"','')
    elif name=='edge':
        text=text.replace('lda #256','lda #1024').replace('lda #$0600','lda #$0300')
        text=replace(text,'edge_save_line:\n  jsl sa1_dma_begin', '  jsl sa1_dma_begin\nedge_save_line:')
        text=replace(text,'  sta $2235\n  jsl sa1_dma_end\n  jsr edge_next', '  sta $2235\n  jsr edge_next')
        text=replace(text,'  bne edge_save_line\n  rtl', '  bne edge_save_line\n  jsl sa1_dma_end\n  rtl')
        text=replace(text,'edge_restore_line:\n  jsl sa1_dma_begin','  jsl sa1_dma_begin\nedge_restore_line:')
        text=replace(text,'  sta $2237\n  jsl sa1_dma_end\n  rep #$20', '  sta $2237\n  rep #$20')
        text=replace(text,'  bne edge_restore_line\n  rtl','  bne edge_restore_line\n  jsl sa1_dma_end\n  rtl')
    return text


def cpu_copy_source(name,text):
    def code(source,bank,length):
        return '  sep #$20\n  lda #$54\n  sta $07ec\n  lda #0\n  sta $07ed\n  lda '+bank+'\n  sta $07ee\n  lda #$6b\n  sta $07ef\n  rep #$30\n  ldx '+source+'\n  ldy #$0700\n  lda '+length+'\n  dec\n  jsl $0007ec\n  lda #$0700\n  sta $07f1\n  sep #$20\n  stz $07f3\n  rep #$20\n'
    if name=='fast':
        a=text.index('  jsl sa1_dma_begin\n  sta $2238');b=text.index('  ldx fbytes',a)
        old=text[a:b]
        text=text[:a]+'  lda $011e\n  beq fast_code_dma\n'+code('fsrc','fsrc+2','fbytes')+'  jmp fast_code_ready\nfast_code_dma:\n  lda fbytes\n'+old+'fast_code_ready:\n'+text[b:]
    elif name=='near':
        a=text.index('  jsl sa1_dma_begin\n  sta $2238');b=text.index('  ldx nlength',a)
        old=text[a:b]
        text=text[:a]+'  lda $011e\n  beq near_code_dma\n  lda ncode\n  clc\n  adc nstart\n  sta $9a\n'+code('$9a','#$fe','nlength')+'  jmp near_code_ready\nnear_code_dma:\n  lda nlength\n'+old+'near_code_ready:\n'+text[b:]
    elif name=='renderer':
        a=text.index('  jsl sa1_dma_begin\n  sep #$20\n  lda #$80');b=text.index('  lda codelen\n  sec\n  sbc #4',a)
        old=text[a:b]
        text=text[:a]+'  lda $011e\n  beq row_code_dma\n'+code('codeptr','codeptr+2','codelen')+'  jmp row_code_ready\nrow_code_dma:\n'+old+'row_code_ready:\n'+text[b:]
    return text


def rom_ground(text):
    text=replace(text,'hv: .res 2','hv: .res 3')
    text=replace(text,'_fx_ground_native:\n  php\n  rep #$30','_fx_ground_native:\n  php\n  rep #$30\n  sep #$20\n  stz hv+2\n  rep #$20')
    text=replace(text,'  lda (hv),y','  lda [hv],y')
    text=replace(text,'  lda f:$7e0000,x','  lda f:$000000,x')
    text=replace(text,'  lda f:$7e0001,x','  lda f:$000001,x')
    text=replace(text,'.segment "RODATA"\nground_horizontal_runs:', '.segment "BOOT"\nground_horizontal_runs:')
    text=replace(text,'ground_horizontal_values: .incbin', '.segment "BOOT"\nground_horizontal_values: .incbin')
    return text


def skip_far_clear(text):
    text=replace(text,'  stz bgrow\nclear_tile_row:', '  jsl sa1_clear_far_setup\n  stz bgrow\nclear_tile_row:')
    text=replace(text,'clear_scanline:\n', 'clear_scanline:\n  lda bgdest\n  cmp $f2\n  bcc clear_far_needed\n  cmp $f4\n  bcc clear_far_skip\nclear_far_needed:\n')
    text=text.replace('  lda bgdest\n  clc\n  adc #128\n  sta bgdest', 'clear_far_skip:\n  lda bgdest\n  clc\n  adc #128\n  sta bgdest',1)
    text+='\n.segment "BOOT"\nsa1_clear_far_setup:\n  lda $010c\n  clc\n  adc #77\n  .repeat 7\n    asl\n  .endrepeat\n  sta $f2\n  clc\n  adc #14*128\n  sta $f4\n  rtl\n'
    return text


def packet_shapes(name,text):
    if name=='dirty':
        text=replace(text,'  plx\ndirty_next:', '  plx\n  phx\n  lda dirty_i\n  cmp dirty_count\n  bcs dirty_shape_saved\n  asl\n  tax\n  lda $ba\n  sta f:$433000,x\ndirty_shape_saved:\n  plx\ndirty_next:')
        text=replace(text,'  lda dirty_width\n  jsl sa1_find_shape', '  lda dirty_ptr\n  beq dirty_shape_new\n  lda dirty_i\n  asl\n  tax\n  lda f:$433000,x\n  tax\n  bra dirty_shape_ready\ndirty_shape_new:\n  lda dirty_width\n  jsl sa1_find_shape\n  stx $ba\ndirty_shape_ready:')
    elif name=='renderer':
        text=replace(text,'  lda height\n  xba\n  ora width\n  ldx asset\n  jsl sa1_find_shape', '  lda index\n  asl\n  tax\n  lda f:$433000,x\n  tax')
    return text
