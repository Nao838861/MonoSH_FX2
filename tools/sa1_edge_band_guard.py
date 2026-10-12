"""画面端の退避経路とJIT読み込みを比較するopt-inのsource変換。"""


def change(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def trace(text):
    """命令列を変えず、呼出し前後の計測用labelだけを公開する。"""
    text='.setcpu "65816"\n.export edge_save_completed: far, edge_restore_completed: far\n'+text
    for name in ('save','restore'):
        text=change(text,'  jsl sa1_edge_'+name+'\n','  jsl sa1_edge_'+name+'\nedge_'+name+'_completed:\n')
    return text


def dma_min(text,width):
    for kind in ('save','restore'):
        text=change(text,'  cmp #33\n  bcc edge_'+kind+'_cpu\n',
            '  cmp #'+str(width)+'\n  bcc edge_'+kind+'_cpu\n')
    return text


def jit_limit(text,maximum,prepare=False):
    """幅の広い退避はJITを使わず、元の1024B cache/chunk長を使う。"""
    if prepare:
        return change(text,'  cmp #33\n  jcs small_prepare_done\n',
            '  cmp #'+str(maximum+1)+'\n  jcs small_prepare_done\n')
    for kind in ('save','restore'):
        text=change(text,'edge_'+kind+'_cpu:\n  lda $c4\n  cmp #33\n',
            'edge_'+kind+'_cpu:\n  lda $c4\n  cmp #'+str(maximum+1)+'\n')
    return text


def lazy_jit(text,width_tag=False):
    """形状・chunk寸法は即座に決め、512BのJIT転送だけ最初のCPUコピーまで遅らせる。"""
    text='.setcpu "65816"\n.export sa1_small_edge_load: far, small_prepare_cpu: far, small_prepare_done: far, save_jit_ready: far, restore_jit_ready: far\n'+text
    text=change(text,'sa1_small_edge_prepare:\n  rep #$30\n',
        'sa1_small_edge_prepare:\n  rep #$30\n  stz $01b0\n')
    text=change(text,'  sty $da\n  lda $c4\n',
        '  sty $da\n  rtl\nsa1_small_edge_load:\n  rep #$30\n  lda $c4\n')
    for name in ('save','restore'):
        text=change(text,'sa1_small_edge_'+name+':\n  rep #$30\n',
            'sa1_small_edge_'+name+':\n  rep #$30\n  lda $01b0\n  bne '+name+'_jit_ready\n  jsl sa1_small_edge_load\n  rep #$30\n  lda #1\n  sta $01b0\n'+name+'_jit_ready:\n')
    if width_tag:
        for name in ('save','restore'):
            text=change(text,'  lda $01b0\n  bne '+name+'_jit_ready\n',
                '  lda $01b0\n  cmp $c4\n  beq '+name+'_jit_ready\n')
        assert text.count('  lda #1\n  sta $01b0\n')==2
        text=text.replace('  lda #1\n  sta $01b0\n','  lda $c4\n  sta $01b0\n')
    return text


def band_fast(text):
    text='.setcpu "65816"\n.import sa1_edge_band_init: far, sa1_edge_band_chunk: far\n.export edge_band_initialized: far, edge_band_chunk_ready: far\n'+text
    text=change(text,'  jsl sa1_edge_prepare\n','  jsl sa1_edge_prepare\n  lda $c4\n  sta $01b2\n  stz $01b4\n  beq edge_band_initialized\n  jsl sa1_edge_band_init\nedge_band_initialized:\n')
    text=change(text,'  jsl sa1_edge_save\n','  lda $01b4\n  beq edge_band_chunk_ready\n  jsl sa1_edge_band_chunk\nedge_band_chunk_ready:\n  jsl sa1_edge_save\n')
    return change(text,'  jsl sa1_edge_restore\n','  jsl sa1_edge_restore\n  lda $01b2\n  sta $c4\n')
