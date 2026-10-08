; Experimental exact palette compositor, run after framebuffer/DMA generation.
; SRAM $1000..$12ff is the 768-byte row-major BG attribute map.
; Scratch $0980..$099f / $09c0..$09d7 stores source cell columns / rows.
; Header $0004/$0006 and $000c..$001f are reusable after drawing. The DMA
; descriptor count/size at $0008/$000a and all drawing assets stay untouched.
; Packet order already excludes OBJ/blinking commands and is stable depth order.
; Each covered output tile samples its clamped center using the original Q8.8
; steps. Transparent source cells do not replace an earlier palette assignment.
.export gsu_color_begin, gsu_color_done, gsu_color_setup_cache
.export gsu_color_axis_cache, gsu_color_draw_cache, gsu_color_draw_cache_end
.align 16,$01
gsu_color_begin:
  cache
  ibt r0,#$5e
  romb
  ; The immutable baseline has only three row patterns, each used by 8 rows.
  ; Keep a word value in R0 until its two attribute bytes change. This replaces
  ; 768 ROM byte reads with word stores while preserving tile-number bits 0..1.
  iwt r1,#$1000
  .repeat 3,Group
    .scope .ident(.sprintf("GsuColorClear%d",Group))
    ibt r12,#8
    iwt r13,#.loword(clear_rows)
clear_rows:
    .repeat 16,Pair
      .if Pair=0 .or (($20|(((Pair*2)*24+Group*8)>>8))|(($20|(((Pair*2+1)*24+Group*8)>>8))<<8)) <> (($20|((((Pair-1)*2)*24+Group*8)>>8))|(($20|((((Pair-1)*2+1)*24+Group*8)>>8))<<8))
        iwt r0,#(($20|(((Pair*2)*24+Group*8)>>8))|(($20|(((Pair*2+1)*24+Group*8)>>8))<<8))
      .endif
      stw (r1)
      inc r1
      .if Pair=15
        loop
      .endif
      inc r1               ; final INC is the LOOP delay slot
    .endrepeat
    .endscope
  .endrepeat
.export gsu_color_clear_end
gsu_color_clear_end:
  lms r0,($0000)
  sms ($0004),r0
  ibt r0,#$20
  sms ($0006),r0
  iwt r11,#.loword(gsu_color_setup_cache)
  jmp (r11)
  nop

.assert *-gsu_color_begin <= 512, error, "GSU color clear cache overflow"

; Setup remains separate from the drawing renderer's fixed 511-byte cache.
.align 16,$01
gsu_color_setup_cache:
  cache
gsu_color_next:
  lms r0,($0004)
  ibt r8,#0
  cmp r8
  bne gsu_color_have_packet
  nop
  iwt r11,#.loword(gsu_color_delta_begin)
  jmp (r11)
  nop
gsu_color_have_packet:
  dec r0
  sms ($0004),r0
  lms r11,($0006)
  from r11
  add #10
  sms ($0006),r0
  to r1
  ldw (r11)                 ; center X
  inc r11
  inc r11
  to r2
  ldw (r11)                 ; bottom Y
  inc r11
  inc r11
  ldw (r11)                 ; width/height
  move r4,r0
  iwt r8,#$00ff
  and r8
  sms ($0010),r0            ; width
  lsr
  move r3,r0
  from r1
  sub r3
  sms ($000c),r0            ; left = center-floor(width/2)
  from r4
  swap
  and r8
  sms ($0012),r0            ; height
  move r3,r0
  from r2
  sub r3
  ibt r8,#20
  sub r8
  sms ($000e),r0            ; top = bottom-height-20
  inc r11
  inc r11
  ldw (r11)
  sms ($0014),r0            ; asset/flags
  lms r0,($0010)
  ibt r8,#0
  cmp r8
  beq gsu_color_next
  nop
  lms r0,($0012)
  cmp r8
  beq gsu_color_next
  nop
  ; X axis: build one source-cell index for each covered output tile column.
  lms r1,($000c)
  lms r2,($0010)
  iwt r3,#256
  ibt r7,#16
  iwt r8,#$0980
  ibt r9,#0
  iwt r10,#$b000
  iwt r11,#.loword(gsu_color_x_done)
  iwt r12,#.loword(gsu_color_axis_cache)
  jmp (r12)
  nop
gsu_color_x_done:
  sms ($0016),r10           ; first tile X
  sms ($0018),r2            ; number of tile columns
  ibt r4,#0
  from r2
  cmp r4
  bne gsu_color_y_begin
  nop
  iwt r11,#.loword(gsu_color_setup_cache)
  jmp (r11)
  nop
gsu_color_y_begin:
  lms r1,($000e)
  lms r2,($0012)
  iwt r3,#192
  ibt r7,#32
  iwt r8,#$09c0
  iwt r9,#$5800
  iwt r10,#$b02c
  iwt r11,#.loword(gsu_color_y_done)
  iwt r12,#.loword(gsu_color_axis_cache)
  jmp (r12)
  nop
gsu_color_y_done:
  sms ($001a),r10           ; first tile Y
  sms ($001c),r2            ; number of tile rows
  ibt r4,#0
  from r2
  cmp r4
  bne gsu_color_draw_begin
  nop
  iwt r11,#.loword(gsu_color_setup_cache)
  jmp (r11)
  nop
gsu_color_draw_begin:
  iwt r11,#.loword(gsu_color_draw_cache)
  jmp (r11)
  nop
gsu_color_setup_end:
.assert gsu_color_setup_end-gsu_color_setup_cache <= 512, error, "GSU color setup cache overflow"

; Axis input: R1 origin, R2 extent, R3 screen extent, R7 flip flag mask,
; R8 destination byte array, R9 UV table base, R10 source-dimension table,
; R11 return PC. Output R10 first covered tile, R2 covered tile count.
; LMULT's low word is exact even when the signed Q8.8 step is negative.
.align 16,$01
gsu_color_axis_cache:
  nop                      ; preserve setup's common color CBR, no reload
  lms r0,($0014)
  ibt r4,#63
  and r4
  move r5,r0
  from r2
  add r2
  move r4,r0
  from r5
  swap
  add r0
  add r4
  to r14
  add r9
  getb
  inc r14
  getbh
  move r6,r0               ; DU or DV, from unchanged $5E division tables
  from r5
  to r14
  add r10
  getb
  swap
  dec r0
  move r10,r0              ; source dimension*256-1
  lms r0,($0014)
  swap
  and r7
  beq gsu_color_axis_forward
  nop
  ibt r0,#0
  to r6
  sub r6
  move r7,r10
  bra gsu_color_axis_bounds
  nop
gsu_color_axis_forward:
  ibt r7,#0
gsu_color_axis_bounds:
  from r1
  add r2
  dec r0                   ; last covered screen pixel before clipping
  bmi gsu_color_axis_empty
  nop
  cmp r3
  blt gsu_color_axis_end_clipped
  nop
  move r0,r3
  dec r0
gsu_color_axis_end_clipped:
  lsr
  lsr
  lsr
  move r9,r0               ; last tile index
  moves r0,r1
  bpl gsu_color_axis_first_positive
  nop
  ibt r0,#0
gsu_color_axis_first_positive:
  lsr
  lsr
  lsr
  move r10,r0              ; first tile index
  from r9
  sub r10
  bmi gsu_color_axis_empty
  nop
  inc r0
  move r12,r0
  move r9,r2
  dec r9                   ; maximum clamped destination-space sample
  move r2,r12              ; preserve original loop count for caller
  from r10
  add r10
  add r0
  add r0
  add #4
  sub r1
  move r5,r0               ; raw first tile center relative to sprite
  iwt r13,#.loword(gsu_color_axis_sample)
gsu_color_axis_sample:
  moves r0,r5
  bpl gsu_color_axis_sample_positive
  nop
  ibt r0,#0
gsu_color_axis_sample_positive:
  cmp r9
  blt gsu_color_axis_sample_clamped
  nop
  move r0,r9
gsu_color_axis_sample_clamped:
  lmult
  from r4
  add r7
  swap
  lsr
  lsr
  lsr
  and #15                  ; floor(Q8.8 / 2048), exact source cell 0..15
  stb (r8)
  with r5
  add #8
  loop
  inc r8
  jmp (r11)
  nop
gsu_color_axis_empty:
  ibt r2,#0
  jmp (r11)
  nop
gsu_color_axis_end:
.assert gsu_color_axis_end-gsu_color_axis_cache <= 512, error, "GSU color axis cache overflow"

; The nested compositor reuses precomputed exact source cell X/Y coordinates.
; R1 output, R2 remaining rows, R3 X-index pointer, R4 baseline attribute pointer,
; R5 next output row, R6 source asset base, R7 current source row base,
; R8 Y-index pointer, R9 columns, R10 transparency test zero, R11 scratch.
.align 16,$01
gsu_color_draw_cache:
  nop                      ; axis + compositor share setup's <=512-byte cache
  lms r0,($0014)
  ibt r11,#63
  and r11
  swap
  iwt r11,#$c000
  add r11
  move r6,r0
  lms r0,($001a)
  .repeat 5
    add r0
  .endrepeat
  lms r11,($0016)
  add r11
  iwt r11,#$1000
  add r11
  move r5,r0
  lms r2,($001c)
  lms r9,($0018)
  iwt r8,#$09c0
  ibt r10,#0
gsu_color_row:
  ldb (r8)
  .repeat 4
    add r0
  .endrepeat
  add r6
  move r7,r0
  inc r8
  move r1,r5
  iwt r3,#$0980
  move r12,r9
  iwt r13,#.loword(gsu_color_cell)
gsu_color_cell:
  ldb (r3)
  to r14
  add r7
  ; Fetch the immutable destination tile-number bits while palette ROM is
  ; pending. Opaque cells avoid serial ROM-then-SRAM stalls; transparent cells
  ; incur the harmless extra read but never write to the previous palette.
  to r11
  ldb (r1)
  with r11
  and #3
  getb
  cmp r10
  beq gsu_color_transparent
  nop
  or r11
  stb (r1)
gsu_color_transparent:
  inc r3
  loop
  inc r1
  ibt r0,#32
  with r5
  add r0
  dec r2
  bne gsu_color_row
  nop
  iwt r11,#.loword(gsu_color_setup_cache)
  jmp (r11)
  nop
gsu_color_draw_cache_end:
.assert gsu_color_draw_cache_end-gsu_color_draw_cache <= 512, error, "GSU color draw cache overflow"
.assert gsu_color_draw_cache_end-gsu_color_setup_cache <= 512, error, "GSU common color cache overflow"

; Palette DMA delta plan. CPU uploads this generation before starting the next
; GSU render. Shadow is therefore the last map accepted for presentation.
; SRAM $1300..$15ff: previous attribute bytes.
; SRAM $1600: descriptor count, $1602: transferred bytes, $1604: shadow valid.
; SRAM $1620: up to 12 [$4000 + row-major byte offset, length bytes] records.
; CPU must reset the 16-bit shadow-valid word to zero on initialization.
; Changed words are widened to even-byte boundaries; gaps <=64 bytes are sent
; together. Even the maximally fragmented 768-byte map needs at most 12 spans:
; consecutive separated spans must start at least 68 bytes apart.
.export gsu_color_delta_begin, gsu_color_delta_end
.align 16,$01
gsu_color_delta_begin:
  cache
  iwt r1,#$1604
  ldw (r1)
  ibt r10,#0
  cmp r10
  bne gsu_color_delta_scan_setup
  nop
  ibt r0,#1
  stw (r1)
  iwt r1,#$1000
  iwt r2,#$1300
  iwt r12,#384
  iwt r13,#.loword(gsu_color_shadow_init)
gsu_color_shadow_init:
  ldw (r1)
  stw (r2)
  inc r1
  inc r2
  inc r1
  loop
  inc r2
gsu_color_delta_full:
  iwt r6,#$1620
  iwt r0,#$4000
  stw (r6)
  inc r6
  inc r6
  iwt r8,#768
  from r8
  stw (r6)
  ibt r7,#1
  iwt r11,#.loword(gsu_color_delta_metadata)
  jmp (r11)
  nop

gsu_color_delta_scan_setup:
  iwt r1,#$1000
  iwt r2,#$1300
  iwt r4,#$ffff             ; active span SRAM address, or no active span
  ibt r5,#0                 ; exclusive active span end
  iwt r6,#$1620
  ibt r7,#0                 ; span count, including the active span
  ibt r8,#0                 ; total closed-span bytes
  ibt r9,#65                ; split when unchanged gap >=65 bytes
  iwt r10,#$ffff
  iwt r14,#$3000            ; SRAM $1000 + $3000 = legacy VRAM base $4000
  iwt r12,#384
  iwt r13,#.loword(gsu_color_delta_word)
gsu_color_delta_word:
  to r11
  ldw (r1)
  ldw (r2)
  cmp r11
  beq gsu_color_delta_same
  nop
  from r11
  stw (r2)                  ; shadow always advances, even after full fallback
  from r4
  cmp r10
  bne gsu_color_delta_have_span
  nop
  inc r7
  move r4,r1
  bra gsu_color_delta_extend
  nop
gsu_color_delta_have_span:
  from r1
  sub r5
  cmp r9
  blt gsu_color_delta_extend
  nop
  ; Close the previous changed run before beginning a distant one.
  from r4
  add r14
  stw (r6)
  inc r6
  inc r6
  from r5
  sub r4
  stw (r6)
  with r8
  add r0
  inc r6
  inc r6
  inc r7
  move r4,r1
gsu_color_delta_extend:
  from r1
  add #2
  move r5,r0
gsu_color_delta_same:
  inc r1
  inc r2
  inc r1
  loop
  inc r2
  ibt r10,#0
  from r7
  cmp r10
  beq gsu_color_delta_metadata
  nop
  from r4
  add r14
  stw (r6)
  inc r6
  inc r6
  from r5
  sub r4
  stw (r6)
  with r8
  add r0
  ; Safety fallback. The 64-byte coalescing rule mathematically bounds this
  ; 768-byte map to 12 runs, but never expose a larger list to the CPU.
  ibt r10,#13
  from r7
  cmp r10
  blt gsu_color_delta_metadata
  nop
  iwt r11,#.loword(gsu_color_delta_full)
  jmp (r11)
  nop
gsu_color_delta_metadata:
  sm ($1600),r7
  sm ($1602),r8
gsu_color_delta_end:
.assert gsu_color_delta_end-gsu_color_delta_begin <= 512, error, "GSU color delta cache overflow"
gsu_color_done:
