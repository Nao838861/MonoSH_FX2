.ifndef SA1_CC_BUFFER
SA1_CC_BUFFER = $05c0
.endif
; 表示より最大二画像先まで処理する。metadataの三枠は地面の三重bufferと対応する。
.import fx_obj_next, fx_obj_present, player4_next, player4_present
.export pipe_irq, irq_game, prefetch_finished
.export pipe_front_slot, pipe_target_slot, pipe_records, pipe_missed, pipe_pending
.export pipe_obj_pointer
.export pipe_status, pipe_complete, pipe_presented_irq, pipe_bw_busy
.export pipe_render_slot
.export pipe_irq_done, pipe_irq_transfer, pipe_wait_dma
.export pipe_irq_exit
.export pipe_dma_measured_end
.segment "COLORBSS"
pipe_records: .res 512*SA1_PIPELINE_DEPTH
.segment "BSS"
pipe_initialized: .res 2
pipe_write_slot: .res 2
pipe_read_slot: .res 2
pipe_render_slot: .res 2
pipe_front_slot: .res 2
pipe_target_slot: .res 2
pipe_pending: .res 2
pipe_complete: .res 2
pipe_next_bw: .res 2
.ifdef SA1_TRIPLE_BW
pipe_bw_busy: .res 6
.else
pipe_bw_busy: .res 4
.endif
pipe_status: .res 2*SA1_PIPELINE_DEPTH
pipe_submitted: .res 2
pipe_missed: .res 2
pipe_irq_phase: .res 2
pipe_presented_irq: .res 2
pipe_budget: .res 2
pipe_record_offset: .res 2
pipe_main_offset: .res 2
pipe_next_slot: .res 2
pipe_copy_length: .res 2
pipe_collect_length: .res 2
pipe_available: .res 2
pipe_line: .res 2
pipe_obj_pointer: .res 2
pipe_desc_offset: .res 2
pipe_dma_chunk: .res 2
pipe_fast_end: .res 2
pipe_fast_page: .res 2
.segment "BOOT"
irq_game:
  php
  rep #$30
  pha
  phx
  phy
  phd
  phb
  lda #0
  tcd
  sep #$20
  lda #$7e
  pha
  plb
  jml $7f0000+pipe_irq
.segment "CODE"
.a8
.i8
_fx_present:
  php
  rep #$30
  lda pipe_initialized
  bne pipe_main
  inc pipe_initialized
  .if SA1_PIPELINE_DEPTH > 3
  .import pipe_ground_extra, pipe_ground_extra_end
  ldx #pipe_ground_extra_end-pipe_ground_extra-2
pipe_clear_ground:
  stz pipe_ground_extra,x
  dex
  dex
  bpl pipe_clear_ground
  .endif
  lda #$ffff
  sta pipe_front_slot
  sta pipe_target_slot
  lda #203
  sta f:$004209
  sep #$20
  .ifdef SA1_PIPELINE_IRQ
  lda #$80
  sta f:$002201
  .endif
  lda #$a1
  sta f:$004200
  rep #$30
pipe_main:
  cli
  stz fx4_build_skip
pipe_wait_bw:
  jsr pipe_collect
  ldx pipe_next_bw
  lda pipe_bw_busy,x
  bne pipe_wait_bw
  lda pipe_write_slot
  asl
  tax
  lda pipe_status,x
  bne pipe_wait_bw
  lda #1
  sta pipe_status,x
  lda pipe_write_slot
  .repeat 9
    asl
  .endrepeat
  sta pipe_main_offset
  tax
  lda pipe_next_bw
  lsr
  clc
  .ifdef SA1_PIPELINE_DIRECT
  adc #$40
  .else
  adc #$41
  .endif
  sta pipe_records,x
  sta f:$003102
  inc pipe_submitted
  lda pipe_submitted
  sta pipe_records+8,x
  lda _fx_far_d_acc
  .repeat 7
    lsr
  .endrepeat
  and #511
  sta pipe_records+10,x
  sta f:$003108
  lda _fx_far_u_acc
  .repeat 7
    lsr
  .endrepeat
  and #511
  sta pipe_records+12,x
  sta f:$00310a
  lda _monosh_ground_offset
  and #255
  sta pipe_records+14,x
  sta f:$00310c
  lda _fx_packet_count
  sta pipe_records+16,x
  sta f:$003106
  lda player4_next
  sta pipe_records+18,x
  lda _fx_ground_vptr
  sta pipe_records+20,x
  lda _fx_ground_c1ptr
  sta pipe_records+22,x
  lda _fx_ground_c3ptr
  sta pipe_records+24,x
  lda _fx_ground_hptr
  sta pipe_records+26,x
  lda _fx_ground_far_xptr
  sta pipe_records+28,x
  lda _fx_ground_far_y
  sta pipe_records+30,x
  lda fx_sky_pointer
  sta pipe_records+32,x
  txa
  clc
  adc #pipe_records+64
  tay
  ldx #fx_obj_next
  lda #135
  mvn #$7e,#$7e
  ; channel0の設定途中にPPU IRQを入れない。
  php
  sei
  jsr fx_upload_ground
  plp
  lda _fx_packet_count
  asl
  asl
  clc
  adc _fx_packet_count
  asl
  sta pipe_copy_length
  beq pipe_no_packet
  ; WRAM port????DMA??????packet?BW-RAM????
  php
  sei
  lda #_fx_packet
  sta f:$002181
  lda #$8080
  sta f:$004300
  lda #0
  sta f:$004302
  sep #$20
  sta f:$002183
  lda #$43
  sta f:$004304
  rep #$20
  lda pipe_copy_length
  sta f:$004305
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
  plp
pipe_no_packet:
  ldx pipe_next_bw
  lda #1
  sta pipe_bw_busy,x
  lda pipe_next_bw
  .ifdef SA1_TRIPLE_BW
  inc
  inc
  cmp #6
  bcc :+
  lda #0
:
  .else
  eor #2
  .endif
  sta pipe_next_bw
  lda pipe_write_slot
  sta pipe_render_slot
  inc pipe_pending
render_started:
  lda #1
  sta f:$003100
  lda pipe_write_slot
  inc
  cmp #SA1_PIPELINE_DEPTH
  bcc :+
  lda #0
:
  sta pipe_next_slot
  sep #$30
  jsr _fx_frame
logic_finished:
  rep #$30
pipe_wait_render:
  .ifdef SA1_PIPELINE_IRQ
  sei
  .endif
  jsr pipe_collect
  lda pipe_pending
  beq pipe_render_ready
  .ifdef SA1_PIPELINE_IRQ
  wai
  cli
  .endif
  bra pipe_wait_render
pipe_render_ready:
  cli
render_finished:
render_second_started:
render_second_finished:
  jsl fx_audio_process
audio4_first_done:
audio4_second_done:
  rep #$30
  lda pipe_next_slot
  sta pipe_write_slot
  plp
  cli
  rts

.export pipe_ground_wait
pipe_ground_wait:
  php
  rep #$30
  pha
  phx
  lda pipe_next_slot
  asl
  tax
pipe_ground_busy:
  jsr pipe_collect
  lda pipe_status,x
  bne pipe_ground_busy
  plx
  pla
  plp
  rts

; mainとIRQの両方から呼ぶ。metadataを完成させてからreadyを公開する。
pipe_collect:
  php
  sei
  rep #$30
  pha
  phx
  phy
  phb
  lda pipe_pending
  beq pipe_collect_end
  lda f:$003104
  beq pipe_collect_end
  lda pipe_render_slot
  .repeat 9
    asl
  .endrepeat
  tax
  lda f:$003118
  sta pipe_records+34,x
  lda f:$00311a
  asl
  sta pipe_collect_length
  asl
  clc
  adc pipe_collect_length
  sta pipe_records+2,x
  stz pipe_records+4,x
  beq pipe_collect_publish
  sta f:$004305
  txa
  clc
  adc #pipe_records+208
  sta f:$002181
  .ifdef SA1_TRANSFER_TILES
  lda f:$003014
  .else
  lda #$0800
  .endif
  sta f:$004302
  lda #$8000
  sta f:$004300
  sep #$20
  lda #0
  sta f:$002183
  lda #$43
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$20
pipe_collect_publish:
  lda pipe_render_slot
  asl
  tax
  lda #2
  sta pipe_status,x
  stz pipe_pending
  lda #0
  sta f:$003100
pipe_ack:
  lda f:$003104
  bne pipe_ack
pipe_collect_end:
  plb
  ply
  plx
  pla
  plp
  rts

pipe_irq:
  .a8
  lda f:$004211
  .ifdef SA1_PIPELINE_IRQ
  bmi pipe_vertical_irq
  lda #$80
  sta f:$002202
  rep #$30
  jsr pipe_collect
  jmp pipe_irq_exit
pipe_vertical_irq:
  .endif
  rep #$30
pipe_irq_transfer:
  stz pipe_presented_irq
  lda #3000
  sta pipe_budget
  jsr pipe_collect
  .ifdef SA1_PIPELINE_IRQ
  lda #0
  sta f:$00311c
  .endif
  lda #1
  sta f:$00311e
  .ifdef SA1_PIPELINE_IRQ
  sep #$20
  lda #$80
  sta f:$002200
  rep #$20
  .endif
pipe_wait_dma:
  lda f:$00311c
  cmp #2
  bne pipe_wait_dma
  sep #$20
  lda #$80
  sta f:$002100
  rep #$30
  lda pipe_complete
  beq pipe_choose_target
  jsr pipe_flip
pipe_choose_target:
  jsr pipe_collect
  lda pipe_target_slot
  cmp #$ffff
  bne pipe_setup_transfer
  lda pipe_read_slot
  asl
  tax
  lda pipe_status,x
  cmp #2
  jne pipe_irq_done
  lda #3
  sta pipe_status,x
  lda pipe_read_slot
  sta pipe_target_slot
  .repeat 9
    asl
  .endrepeat
  sta pipe_record_offset
  tax
  lda fx4_page
  eor #$3000
  sta pipe_records+6,x
  stz fx4_dma_bytes
pipe_setup_transfer:
  lda pipe_target_slot
  .repeat 9
    asl
  .endrepeat
  sta pipe_record_offset
  tax
  sep #$20
  lda #$15
  sta f:$002231
  rep #$20
  lda #0
  sta f:$002232
  sep #$20
  lda pipe_records,x
  sta f:$002234
  rep #$20
  lda #SA1_CC_BUFFER
  sta f:$002235
  lda #$1801
  sta f:$004300
  sep #$20
  lda pipe_records,x
  sta f:$004304
  rep #$30
transfer_chunk:
dma_chunk_ready:
  .ifdef SA1_FAST_DMA
  jsr pipe_try_fast_dma
  jcs pipe_transfer_complete
  .endif
pipe_descriptor:
  ldx pipe_record_offset
  lda pipe_records+4,x
  cmp pipe_records+2,x
  jcs pipe_transfer_complete
  clc
  adc pipe_record_offset
  sta pipe_desc_offset
  tax
  jsr pipe_time_left
  lda pipe_records+208,x
  clc
  adc #192
  cmp pipe_available
  bcc pipe_full_descriptor
  lda pipe_available
  cmp #224
  jcc pipe_transfer_pause
  sec
  sbc #192
  and #$ffe0
  bra pipe_set_chunk
pipe_full_descriptor:
  lda pipe_records+208,x
pipe_set_chunk:
  sta pipe_dma_chunk
  sta f:$004305
  clc
  adc fx4_dma_bytes
  sta fx4_dma_bytes
  lda pipe_records+210,x
  sta f:$004302
  lda pipe_records+212,x
  ldx pipe_record_offset
  clc
  adc pipe_records+6,x
  sta f:$002116
  sep #$20
dma_started:
  lda #1
  sta f:$00420b
half_dma_finished:
  rep #$30
  ldx pipe_record_offset
  lda pipe_records+34,x
  sec
  sbc pipe_dma_chunk
  sta pipe_records+34,x
  ldx pipe_desc_offset
  lda pipe_records+208,x
pipe_dma_measured_end:
  sec
  sbc pipe_dma_chunk
  beq pipe_descriptor_complete
  sta pipe_records+208,x
  lda pipe_records+210,x
  clc
  adc pipe_dma_chunk
  sta pipe_records+210,x
  lda pipe_dma_chunk
  lsr
  clc
  adc pipe_records+212,x
  sta pipe_records+212,x
  jmp pipe_descriptor
pipe_descriptor_complete:
  ldx pipe_record_offset
  lda pipe_records+4,x
  clc
  adc #6
  sta pipe_records+4,x
  jmp pipe_descriptor
pipe_transfer_complete:
  sep #$20
  lda #$95
  sta f:$002231
  rep #$30
  ldx pipe_record_offset
  lda pipe_records,x
  sec
  .ifdef SA1_PIPELINE_DIRECT
  sbc #$40
  .else
  sbc #$41
  .endif
  asl
  tax
  stz pipe_bw_busy,x
  lda #1
  sta pipe_complete
prefetch_finished:
  lda pipe_presented_irq
  bne pipe_irq_done
  jsr pipe_flip
  jmp pipe_choose_target
pipe_transfer_pause:
  sep #$20
  lda #$95
  sta f:$002231
  rep #$30
pipe_irq_done:
  lda pipe_presented_irq
  bne :+
  inc pipe_missed
:
  lda #0
  .ifdef SA1_PIPELINE_IRQ
  sep #$20
  sta f:$002200
  rep #$20
  .endif
  sta f:$00311e
pipe_irq_exit:
  rep #$30
  plb
  pld
  ply
  plx
  pla
  plp
  rti

pipe_time_left:
  sep #$20
  lda f:$00213f
  lda f:$002137
  lda f:$00213d
  sta pipe_line
  lda f:$00213d
  and #1
  sta pipe_line+1
  rep #$20
  lda pipe_line
  cmp #203
  bcs :+
  clc
  adc #262
:
  sta pipe_line
  lda #283
  sec
  sbc pipe_line
  bmi pipe_no_time
  sta pipe_available
  asl
  asl
  clc
  adc pipe_available
  asl
  asl
  clc
  adc pipe_available
  asl
  asl
  clc
  adc pipe_available
  asl
  sta pipe_available
  lda pipe_presented_irq
  beq pipe_reserve_flip
  lda pipe_available
  sec
  sbc #700
  bra pipe_reserved
pipe_reserve_flip:
  lda pipe_available
  sec
  sbc #2200
pipe_reserved:
  bmi pipe_no_time
  sta pipe_available
  rts
pipe_no_time:
  stz pipe_available
  rts

.ifdef SA1_FAST_DMA
pipe_try_fast_dma:
  rep #$30
  ldx pipe_record_offset
  lda pipe_records+6,x
  sta pipe_fast_page
  lda pipe_records+2,x
  sec
  sbc pipe_records+4,x
  beq pipe_fast_empty
  asl
  asl
  asl
  asl
  sta pipe_dma_chunk
  lda pipe_records+34,x
  lsr
  lsr
  lsr
  lsr
  lsr
  clc
  adc pipe_records+34,x
  adc pipe_dma_chunk
  sta pipe_dma_chunk
  jsr pipe_time_left
  lda pipe_dma_chunk
  cmp pipe_available
  bcs pipe_fast_unavailable
  lda pipe_records+34,x
  clc
  adc fx4_dma_bytes
  sta fx4_dma_bytes
  lda pipe_records+2,x
  clc
  adc pipe_record_offset
  adc #208
  sta pipe_fast_end
  lda pipe_records+4,x
  clc
  adc pipe_record_offset
  adc #208
  tax
pipe_fast_loop:
  lda pipe_records,x
  sta f:$004305
  lda pipe_records+2,x
  sta f:$004302
  lda pipe_records+4,x
  clc
  adc pipe_fast_page
  sta f:$002116
  sep #$20
  lda #1
  sta f:$00420b
  rep #$20
  inx
  inx
  inx
  inx
  inx
  inx
  cpx pipe_fast_end
  bcc pipe_fast_loop
  ldx pipe_record_offset
  lda pipe_records+2,x
  sta pipe_records+4,x
pipe_fast_empty:
  sec
  rts
pipe_fast_unavailable:
  clc
  rts
.endif

pipe_flip:
  rep #$30
  lda pipe_target_slot
  .repeat 9
    asl
  .endrepeat
  sta pipe_record_offset
  tax
  lda pipe_records+20,x
  sta f:$7e1d04
  lda pipe_records+22,x
  sta f:$7e1d06
  lda pipe_records+24,x
  sta f:$7e1d08
  lda pipe_records+26,x
  sta f:$7e1d0e
  lda pipe_records+28,x
  sta f:$7e1d0c
  lda pipe_records+30,x
  sta f:$7e1d0a
  lda pipe_records+32,x
  sta f:$7e1d16
  lda pipe_records+18,x
  sta player4_present
  lda pipe_records+6,x
  sta fx4_page
  txa
  clc
  adc #pipe_records+64
  sta pipe_obj_pointer
  jsr update_ground_pointers
  sep #$20
  lda f:$7e1d0a
  sta f:$002112
  lda f:$7e1d0b
  sta f:$002112
  jsr fx_upload_obj
  lda fx4_page+1
  .repeat 4
    lsr
  .endrepeat
  sta f:$00210b
  rep #$30
  lda pipe_front_slot
  cmp #$ffff
  beq :+
  asl
  tax
  stz pipe_status,x
:
  lda pipe_target_slot
  sta pipe_front_slot
  asl
  tax
  lda #4
  sta pipe_status,x
  lda #$ffff
  sta pipe_target_slot
  stz pipe_complete
  inc pipe_presented_irq
  inc fx4_generation
  lda pipe_read_slot
  inc
  cmp #SA1_PIPELINE_DEPTH
  bcc :+
  lda #0
:
  sta pipe_read_slot
dma_finished:
  rts
