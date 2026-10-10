"""透明文字を除いて詰める試験用の接続。元の描画と切り離して比較する。"""


def transform(name, text):
    if name == 'renderer':
        old = '  jsl sa1_transfer_mask_prepare\n  jsl sa1_deep_rebase'
        assert text.count(old) == 1
        text = '.setcpu "65816"\n.import sa1_dense_prepare: far\n' + text.replace(old, '  jsl sa1_dense_prepare')
    elif name == 'cpu':
        # CODE bank 内の include はビルダーが試験専用に複製する。
        text = text.replace('.include "pipeline_cpu.inc"', '.include "pipeline_dense.inc"')
        text = text.replace('lda #200\n', 'lda #197\n')
    return text


def pipeline(text):
    # flip 完了後は既に非表示を確認済み。IRQ末尾で同じPPU読出しを繰り返さない。
    old = 'pipe_irq_done:\n  .ifdef SA1_EARLY_REQUEST\n  jsr pipe_start_blank\n  .endif'
    new = 'pipe_irq_done:\n  .ifdef SA1_EARLY_REQUEST\n  lda pipe_presented_irq\n  bne pipe_irq_checked\n  jsr pipe_start_blank\n  .endif'
    assert old in text
    text = text.replace(old, new, 1)
    text = text.replace('  lda #200\n', '  lda #197\n', 1)
    text = text.replace('pipe_line: .res 2', 'pipe_line: .res 2\npipe_hpoint: .res 2', 1)
    old = '  lda f:$002137\n  lda f:$00213d\n  sta pipe_line'
    new = '  lda f:$002137\n  lda f:$00213c\n  sta pipe_hpoint\n  lda f:$00213c\n  and #1\n  sta pipe_hpoint+1\n  lda f:$00213d\n  sta pipe_line'
    assert old in text
    text = text.replace(old, new, 1)
    old = '  lda pipe_line\n  cmp #203\n  bcs :+\n  clc\n  adc #262\n:\n  sta pipe_line'
    new = '''  lda pipe_line
  cmp #203
  bcs dense_budget_line_ready
  cmp #197
  bcc dense_budget_next_field
  stz pipe_hpoint
  lda #203
  bra dense_budget_line_ready
dense_budget_next_field:
  clc
  adc #262
dense_budget_line_ready:
  sta pipe_line'''
    assert old in text
    text = text.replace(old, new, 1)
    old = '  asl\n  sta pipe_available\n  .ifdef SA1_STAGED'
    new = '  asl\n  sta pipe_available\n  lda pipe_hpoint\n  lsr\n  sta pipe_hpoint\n  lda pipe_available\n  sec\n  sbc pipe_hpoint\n  clc\n  adc #128\n  sta pipe_available\n  .ifdef SA1_STAGED'
    assert old in text
    text = text.replace(old, new, 1).replace('sbc #1500','sbc #1300').replace('sbc #2500','sbc #2400')
    text = text.replace('  cmp #200\n  bcs pipe_wait_actual_blank', '  cmp #197\n  bcs pipe_wait_actual_blank', 1)
    old = 'transfer_chunk:\ndma_chunk_ready:\n  .ifdef SA1_EARLY_REQUEST\n  jsr pipe_start_blank\n  .endif'
    assert old in text
    text = text.replace(old, 'transfer_chunk:\ndma_chunk_ready:', 1)
    text = text.replace('  sta pipe_fast_page\n  lda pipe_records+2,x', '  sta pipe_fast_page\n  lda pipe_records+4,x\n  beq :+\n  stz pipe_fast_page\n:\n  lda pipe_records+2,x', 1)
    text = text.replace('  lda fx4_page\n  .ifndef SA1_FRONT_MASK', '  lda fx4_page\n  eor #$3000\n  .ifndef SA1_FRONT_MASK', 1)
    text = text.replace('  lda #1\n  sta pipe_records+44,x', '  lda #0\n  sta pipe_records+44,x', 1)
    text = text.replace('  lda #$15\n  sta f:$002231', '  lda #$01\n  sta f:$002231', 1)
    # DMA を再開する場合、文字データの後は生のタイルマップを読む。
    old = '  sta f:$002235\n  .endif\n  rep #$20\n  lda #$1801'
    new = '  sta f:$002235\n  lda pipe_records+4,x\n  beq :+\n  sep #$20\n  lda #$81\n  sta f:$002231\n:\n  .endif\n  rep #$20\n  lda #$1801'
    assert old in text
    text = text.replace(old, new, 1)
    old = '  lda pipe_records+212,x\n  ldx pipe_record_offset\n  clc\n  adc pipe_records+6,x'
    new = '  lda pipe_records+212,x\n  ldx pipe_record_offset\n  pha\n  lda pipe_records+4,x\n  bne :+\n  pla\n  clc\n  adc pipe_records+6,x\n  bra :++\n:\n  pla\n:\n'
    assert old in text
    text = text.replace(old, new, 1)
    # 一枚目の記述子が終わったら CC を停止する。
    old = '  sta pipe_records+4,x\n  jmp pipe_descriptor'
    new = '  sta pipe_records+4,x\n  sep #$20\n  lda #$81\n  sta f:$002231\n  rep #$20\n  jmp pipe_descriptor'
    assert old in text
    text = text.replace(old, new, 1)
    # マップだけは全記述子が収まることを確認してから更新する。
    old = 'pipe_descriptor:\n  ldx pipe_record_offset'
    new = '''pipe_descriptor:
  ldx pipe_record_offset
  lda pipe_records+4,x
  beq dense_descriptor_ready
  lda pipe_records+34,x
  sta pipe_dma_chunk
  jsr pipe_time_left
  lda pipe_dma_chunk
  clc
  adc #1024
  cmp pipe_available
  jcs pipe_transfer_pause
dense_descriptor_ready:
  jsr pipe_start_blank
  ldx pipe_record_offset'''
    text = text.replace(old, new, 1)
    # 完全転送は一枚目を別に送り、残りを生のBW-RAMから読む。
    start = text.index('pipe_fast_loop:\n')
    end = text.index('  .endif\n  ldx pipe_record_offset\npipe_fast_done:', start)
    text = text[:start] + '''pipe_fast_loop:
  lda pipe_records,x
  sta f:$004305
  lda pipe_records+2,x
  sta f:$004302
  lda pipe_records+4,x
  cpx pipe_desc_offset
  bne :+
  clc
  adc pipe_fast_page
:
  sta f:$002116
  sep #$20
  lda #1
  sta f:$00420b
  lda #$81
  sta f:$002231
  rep #$20
  txa
  clc
  adc #6
  tax
  cpx pipe_fast_end
  bcc pipe_fast_loop
''' + text[end:]
    old = '  tax\npipe_fast_begin:'
    assert old in text
    text = text.replace(old, '  tax\n  stx pipe_desc_offset\npipe_fast_begin:', 1)
    text = text.replace('pipe_fast_begin:\n', '  jsr pipe_start_blank\npipe_fast_begin:\n', 1)
    return text
