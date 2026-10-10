; recordの二組のdescriptorから今回の面を選ぶ。
; X=record offset。carry=0なら次のfieldを待ち、readyは維持する。
pipe_adaptive_select:
  rep #$30
  lda fx4_page
  beq av_cpu_front_zero
  lda pipe_records+36,x
  sta pipe_dma_chunk
  lda pipe_records+38,x
  bra av_cpu_cost
av_cpu_front_zero:
  lda pipe_records+2,x
  sta pipe_dma_chunk
  lda pipe_records+34,x
av_cpu_cost:
  sta pipe_budget
  lda pipe_dma_chunk
  .repeat 4
    asl
  .endrepeat
  sta pipe_dma_chunk
  lda pipe_budget
  .repeat 5
    lsr
  .endrepeat
  clc
  adc pipe_budget
  adc pipe_dma_chunk
  cmp #10501
  bcs av_cpu_back
  lda pipe_presented_irq
  bne av_cpu_defer
  lda #1
  sta pipe_records+44,x
  lda fx4_page
  bra av_cpu_choose
av_cpu_back:
  stz pipe_records+44,x
  lda fx4_page
  eor #$3000
av_cpu_choose:
  sta pipe_records+6,x
  beq av_cpu_page_zero
  lda pipe_records+38,x
  sta pipe_records+34,x
  lda pipe_records+36,x
  clc
  adc #144
  sta pipe_records+2,x
  lda #144
  sta pipe_records+4,x
  sec
  rts
av_cpu_page_zero:
  stz pipe_records+4,x
  sec
  rts
av_cpu_defer:
  clc
  rts

pipe_adaptive_publish:
  rep #$30
  ldx pipe_record_offset
  lda pipe_records+6,x
  beq av_cpu_publish_zero
  sep #$20
  lda pipe_records+8,x
  sta f:$00318b
  rep #$20
  rts
av_cpu_publish_zero:
  sep #$20
  lda pipe_records+8,x
  sta f:$00318a
  rep #$20
  rts
