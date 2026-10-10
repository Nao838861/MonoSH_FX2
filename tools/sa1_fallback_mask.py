"""現在のVRAM面の占有集合を使う裏ページ転送の接続。"""


def pipeline(text,early=False):
    text='.import fallback_init: far, fallback_collect: far, fallback_publish: far, fallback_prepare: far\n'+text
    old='  inc pipe_initialized\n'
    assert text.count(old)==1
    text=text.replace(old,old+'  jsl fallback_init\n',1)
    old='pipe_collect_publish:\n'
    assert text.count(old)==1
    text=text.replace(old,old+'  jsl fallback_collect\n',1)
    first=text.index('  lda #6\n  sta pipe_records+2,x',text.index('; 一括転送が収まらない画像'))
    last=text.index('  .endif\n  .ifdef SA1_ADAPTIVE_VRAM',first)
    text=text[:first]+'  jsl fallback_prepare\n  jsr pipe_try_fast_dma\n  jcs pipe_transfer_complete\n'+text[last:]
    old='  lda pipe_front_slot\n  cmp #$ffff'
    assert text.count(old)==1
    text=text.replace(old,'  jsl fallback_publish\n'+old,1)
    if early:
        text=text.replace('  lda #200\n','  lda #190\n',1)
        text=text.replace('  cmp #200\n  bcs pipe_wait_actual_blank','  cmp #190\n  bcs pipe_wait_actual_blank',1)
        old='  lda pipe_line\n  cmp #203\n  bcs :+\n  clc\n  adc #262\n:\n  sta pipe_line'
        new='''  lda pipe_line
  cmp #203
  bcs fb_budget_ready
  cmp #190
  bcc fb_budget_next
  lda #203
  bra fb_budget_ready
fb_budget_next:
  clc
  adc #262
fb_budget_ready:
  sta pipe_line'''
        assert text.count(old)==1
        text=text.replace(old,new,1)
        old='transfer_chunk:\ndma_chunk_ready:\n  .ifdef SA1_EARLY_REQUEST\n  jsr pipe_start_blank\n  .endif'
        assert text.count(old)==1
        text=text.replace(old,'transfer_chunk:\ndma_chunk_ready:',1)
        text=text.replace('pipe_fast_begin:\n','  jsr pipe_start_blank\npipe_fast_begin:\n',1)
        text=text.replace('pipe_descriptor:\n','pipe_descriptor:\n  jsr pipe_start_blank\n',1)
    return text
