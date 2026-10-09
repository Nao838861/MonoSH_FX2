; 描画が先に終わった時だけ、packetの安定ソートをSA-1へ渡す。
; 前画像のmetadataを回収してからjob2を起動する。描画中はS-CPUの既存経路。
.setcpu "65816"
.smart
.macpack longbranch
.import order, keys, pipe_pending, pipe_collect
.importzp packet_work
.import sa1_dma_begin: far, sa1_dma_end: far
.import __SA1SORT_LOAD__, __SA1SORT_SIZE__
.export sa1_try_packet_sort, sa1_sort_job: far
.export packet_sort_attempts, packet_sort_jobs
.segment "BSS"
packet_sort_attempts: .res 2
packet_sort_jobs: .res 2
.segment "CODE"
sa1_try_packet_sort:
  rep #$30
  inc packet_sort_attempts
  lda packet_work+8
  cmp #24
  jcc packet_sort_fallback
  jsr pipe_collect
  lda pipe_pending
  jne packet_sort_fallback
  inc packet_sort_jobs
  lda packet_work+8
  sta f:$003184
  lda #0
  sta f:$003186
  php
  sei
  lda #order
  sta f:$002181
  lda #$8080
  sta f:$004300
  lda #$5000
  sta f:$004302
  lda #256
  sta f:$004305
  sep #$20
  lda #0
  sta f:$002183
  lda #$43
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$20
  plp
  lda #2
  sta f:$003100
packet_sort_wait:
  .repeat 16
    nop
  .endrepeat
  lda f:$003186
  beq packet_sort_wait
  php
  sei
  lda #order
  sta f:$002181
  lda #$8000
  sta f:$004300
  lda #$5000
  sta f:$004302
  lda #256
  sta f:$004305
  sep #$20
  lda #0
  sta f:$002183
  lda #$43
  sta f:$004304
  lda #1
  sta f:$00420b
  rep #$30
  plp
  sec
  rts
packet_sort_fallback:
  clc
  rts

.segment "BOOT"
sa1_sort_job:
  rep #$30
  jsl sa1_dma_begin
  sep #$20
  lda #$80
  sta $2230
  lda #^__SA1SORT_LOAD__
  sta $2234
  rep #$20
  lda #__SA1SORT_SIZE__
  sta $2238
  lda #.loword(__SA1SORT_LOAD__)
  sta $2232
  lda #$0700
  sta $2235
  sep #$20
  lda #$81
  sta $2230
  lda #$43
  sta $2234
  rep #$20
  lda #256
  sta $2238
  lda #$5000
  sta $2232
  lda #$0300
  sta $2235
  jsl sa1_dma_end
  jsl $000700
  jsl sa1_dma_begin
  sep #$20
  lda #$86
  sta $2230
  rep #$20
  lda #256
  sta $2238
  lda #$0300
  sta $2232
  lda #$5000
  sta $2235
  sep #$20
  lda #$43
  sta $2237
  jsl sa1_dma_end
  rep #$30
  stz $0100
  lda #1
  sta $0186
  rtl

.segment "SA1SORT"
  rep #$30
  lda #2
  sta $a0
sort_job_next:
  lda $a0
  cmp $0184
  bcs sort_job_done
  tay
  lda $0300,y
  sta $a2
  lda $0380,y
  sta $a4
  dey
  dey
sort_job_compare:
  lda $0380,y
  cmp $a4
  bcc sort_job_insert
  beq sort_job_insert
  sta $0382,y
  lda $0300,y
  sta $0302,y
  dey
  dey
  bpl sort_job_compare
sort_job_insert:
  iny
  iny
  lda $a2
  sta $0300,y
  lda $a4
  sta $0380,y
  inc $a0
  inc $a0
  bra sort_job_next
sort_job_done:
  rtl
