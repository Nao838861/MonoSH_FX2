SECTION code_compiler

PUBLIC _monosh_camera_fast_update
PUBLIC _monosh_keyboard_action_keys
PUBLIC _monosh_ground_bitmap_present
PUBLIC _monosh_ground_bitmap_begin_direct
PUBLIC _monosh_projection_direct
PUBLIC _monosh_projection_near_direct
PUBLIC _monosh_ground_depth_select
EXTERN _monosh_projection_near_rows
EXTERN _monosh_player_bottom
EXTERN _monosh_ground_offset
EXTERN _monosh_ground_screen_delta
EXTERN _monosh_ground_offset_by_height
EXTERN _ground_irq_line_offset
EXTERN _monosh_ground_page_ready
EXTERN _monosh_ground_front_page
EXTERN _monosh_ground_back_page
EXTERN _monosh_ground_page_flip_count
EXTERN _monosh_ground_page_repeat_count
EXTERN _monosh_far_u_scroll_high
EXTERN _monosh_far_u_scroll_low
EXTERN _monosh_ground_page_u_offset
EXTERN _monosh_ground_depth_rows
EXTERN _monosh_runtime_paused
EXTERN _monosh_runtime_pause_key_down
EXTERN _monosh_runtime_fire_key_down
EXTERN _monosh_runtime_fire_actions
EXTERN _monosh_runtime_reverse_y
EXTERN _monosh_runtime_cursor_input
EXTERN _monosh_player_invuln
EXTERN _monosh_ground_command_active
EXTERN _monosh_ground_command_stage
EXTERN _monosh_ground_fast_begin
EXTERN _gb_issue
EXTERN _v9968_wait_command
EXTERN GET_P2
EXTERN PUT_P2

SECTION rodata_compiler

; MSX keyboard row 8 high nibble is LEFT,UP,DOWN,RIGHT.  games.h expects
; RIGHT,LEFT,DOWN,UP in bits 0..3.  SPACE is intentionally omitted because
; firing is owned by Z/X.
monosh_keyboard_cursor_lut:
    defb $00,$02,$08,$0a,$04,$06,$0c,$0e
    defb $01,$03,$09,$0b,$05,$07,$0d,$0f

SECTION bss_compiler
PUBLIC _monosh_ground_depth_pointer
_monosh_ground_depth_pointer: defs 2
monosh_ground_direct_old_bank: defs 1
monosh_ground_present_r26: defs 1

SECTION data_compiler
; Invalid at startup, so the first legal 0..64 row is always selected.
monosh_ground_depth_loaded_offset: defb $ff

SECTION code_compiler

; H=offset, L=phase.  The generic __banked C call swaps to a temporary stack
; and dispatches through a far-call thunk every field.  Runtime itself is in
; the fixed window, so map bank 7 only around the existing ground builder and
; restore the mapper state before returning.
_monosh_ground_bitmap_begin_direct:
    ld a,(_monosh_ground_command_active)
    or a
    ret nz
    ld a,(_monosh_ground_page_ready)
    or a
    ret nz
    push hl
    call GET_P2
    ld (monosh_ground_direct_old_bank),a
    ld a,7
    call PUT_P2
    pop hl
    call _monosh_ground_fast_begin
monosh_ground_direct_prestripe_loop:
    ld a,(_monosh_ground_command_active)
    or a
    jr z,monosh_ground_direct_restore
    ld a,(_monosh_ground_command_stage)
    cp 3
    jr nc,monosh_ground_direct_restore
    call _v9968_wait_command
    call _gb_issue
    jr monosh_ground_direct_prestripe_loop
monosh_ground_direct_restore:
    ld a,(monosh_ground_direct_old_bank)
    jp PUT_P2

; Read the controls directly because the custom VBlank handler skips the BIOS
; keyboard scanner.  Cursor keys use row 8; Z/X share row 5 bits 7/5; R/P/O
; use row 4 bits 7/5/4.  Combining all three rows replaces joystick(1) plus a
; second PPI transaction on every field.
; Z, R, P and O are edge-triggered. X is returned on every held field.
; pause_key_down and fire_key_down retain their previous physical masks,
; while invulnerability $ff is the persistent O-key sentinel.
_monosh_keyboard_action_keys:
    di
    in a,($aa)
    ld b,a
    and $f0
    or 8
    out ($aa),a
    in a,($a9)
    cpl
    and $f0
    rrca
    rrca
    rrca
    rrca
    ld l,a
    ld h,0
    ld de,monosh_keyboard_cursor_lut
    add hl,de
    ld a,(hl)
    ld (_monosh_runtime_cursor_input),a
    ld a,b
    and $f0
    or 5
    out ($aa),a
    in a,($a9)
    cpl
    ld e,a
    ld a,b
    and $f0
    or 4
    out ($aa),a
    in a,($a9)
    cpl
    ld d,a
    ld a,b
    out ($aa),a
    ei
    ld a,d
    and $b0
    ld c,a
    ld a,(_monosh_runtime_pause_key_down)
    cpl
    and c
    ld b,a
    ld a,c
    ld (_monosh_runtime_pause_key_down),a
    bit 5,b
    jr z,monosh_keyboard_no_pause_trigger
    ld a,(_monosh_runtime_paused)
    xor 1
    ld (_monosh_runtime_paused),a
monosh_keyboard_no_pause_trigger:
    bit 4,b
    jr z,monosh_keyboard_no_invuln_trigger
    ld a,(_monosh_player_invuln)
    cp $ff
    sbc a,a
    ld (_monosh_player_invuln),a
monosh_keyboard_no_invuln_trigger:
    bit 7,b
    jr z,monosh_keyboard_no_reverse_trigger
    ld a,(_monosh_runtime_reverse_y)
    xor 1
    ld (_monosh_runtime_reverse_y),a
monosh_keyboard_no_reverse_trigger:
    ld hl,0
    ; L bit 0: a fresh Z trigger.  Holding Z cannot retrigger.
    ld a,e
    and $80
    ld c,a
    ld a,(_monosh_runtime_fire_key_down)
    cpl
    and c
    ld b,a
    ld a,c
    ld (_monosh_runtime_fire_key_down),a
    bit 7,b
    jr z,monosh_keyboard_no_single_fire
    set 0,l
monosh_keyboard_no_single_fire:
    ; L bit 1: X is physically held, enabling the existing repeat cadence.
    bit 5,e
    ret z
    set 1,l
    ret

; Fixed-bank page flip with direct cartridge-VDP output.  The generic C
; register writer and banked presentation path cost nearly half a millisecond
; despite this being only a swap and one R#2 write.
_monosh_ground_bitmap_present:
    ld a,(_monosh_ground_page_ready)
    or a
    jr nz,monosh_ground_present_ready
    ld hl,(_monosh_ground_page_repeat_count)
    inc hl
    ld (_monosh_ground_page_repeat_count),hl
    ld hl,0
    ret
monosh_ground_present_ready:
    ld a,(_monosh_ground_back_page)
    or a
    ld a,$1f
    jr z,monosh_ground_present_register_ready
    ld a,$7f
monosh_ground_present_register_ready:
    di
    out ($89),a
    ld a,$82
    out ($89),a
    ; Present the coarse scroll that belongs to this completed back page,
    ; not the possibly newer accumulator.  R#27 remains zero; its 1..7-dot
    ; edge is undefined on the real V9958/V9968 and caused the vibrating
    ; black strip at the left of the image.
    ld a,(_monosh_ground_back_page)
    or a
    ld e,0
    jr z,monosh_ground_present_scroll_slot_ready
    inc e
monosh_ground_present_scroll_slot_ready:
    ld d,0
    ld hl,_monosh_ground_page_u_offset
    add hl,de
    ld a,(hl)
    srl a
    srl a
    srl a
    ld b,a
    ld a,(monosh_ground_present_r26)
    cp b
    jr z,monosh_ground_present_scroll_ready
    ld a,b
    ld (monosh_ground_present_r26),a
    out ($89),a
    ld a,$9a
    out ($89),a
monosh_ground_present_scroll_ready:
    ; R#27 is fixed to zero during initialization; rewriting that unchanged
    ; register every field only consumed cartridge I/O cycles.
    ei
    ld a,(_monosh_ground_front_page)
    ld b,a
    ld a,(_monosh_ground_back_page)
    ld (_monosh_ground_front_page),a
    ld a,b
    ld (_monosh_ground_back_page),a
    xor a
    ld (_monosh_ground_page_ready),a
    ld hl,(_monosh_ground_page_flip_count)
    inc hl
    ld (_monosh_ground_page_flip_count),hl
    ld hl,1
    ret

; Update the vertical camera once per 60 Hz field.  All legal middle-row
; targets are a direct ROM lookup; clamping and signed 16-bit C comparisons
; are reduced to byte branches because player_bottom is always 56..201.
_monosh_camera_fast_update:
    ld hl,(_monosh_player_bottom)
    ld a,h
    or a
    jr nz,monosh_camera_target_near
    ld a,l
    cp 57
    jr c,monosh_camera_target_far
    cp 201
    jr nc,monosh_camera_target_near
    sub 56
    ld e,a
    ld d,0
    ld hl,_monosh_ground_offset_by_height
    add hl,de
    ld b,(hl)
    jr monosh_camera_target_ready
monosh_camera_target_far:
    ld b,0
    jr monosh_camera_target_ready
monosh_camera_target_near:
    ld b,64
monosh_camera_target_ready:
    ld a,(_monosh_ground_offset)
    cp b
    jr z,monosh_camera_unchanged
    jr c,monosh_camera_increment
    dec a
    jr monosh_camera_store
monosh_camera_increment:
    inc a
monosh_camera_store:
    ld (_monosh_ground_offset),a
    ld (_ground_irq_line_offset),a
    sub 28
    ld (_monosh_ground_screen_delta),a
    ld hl,1
    ret
monosh_camera_unchanged:
    ld (_ground_irq_line_offset),a
    ld hl,0
    ret

; A = doubled source camera offset (0..64).  MonoSH selects a gy-table pointer;
; do the same here.  The former ROM-to-RAM LDIR copied 81 bytes on every field
; while the player moved vertically, even though Stage only needs a new base
; address.  The rows now live in the renderer's permanently mapped bank 3.
_monosh_ground_depth_select:
    ld b,a
    ld a,(monosh_ground_depth_loaded_offset)
    cp b
    ret z
    ld a,b
    ld (monosh_ground_depth_loaded_offset),a
    ld e,a
    ld d,0
    ld l,a
    ld h,0
    add hl,hl                 ; 2x
    add hl,hl                 ; 4x
    add hl,hl                 ; 8x
    add hl,hl                 ; 16x
    push hl
    add hl,hl                 ; 32x
    add hl,hl                 ; 64x
    pop bc
    add hl,bc                 ; 80x
    add hl,de                 ; 81x
    ld de,_monosh_ground_depth_rows
    add hl,de
    ld (_monosh_ground_depth_pointer),hl
    ret

; A = Z2 (14..110), C = low byte of |world X|.  Complete projection rows
; occupy mapper banks 8 and 9 at $8000, one 256-byte page per Z level.
; The caller lives in bank 3, which is restored before returning.
; Result: E = floor(distance * scale[z] / 256).
_monosh_projection_direct:
    cp 78
    jr nc,monosh_projection_direct_bank9
    sub 14
    add a,$80
    ld h,a
    ld l,c
    di
    ld a,8
    ld ($7000),a
    ld e,(hl)
    ld a,3
    ld ($7000),a
    ei
    ret
monosh_projection_direct_bank9:
    sub 78
    add a,$80
    ld h,a
    ld l,c
    di
    ld a,9
    ld ($7000),a
    ld e,(hl)
    ld a,3
    ld ($7000),a
    ei
    ret

; A = Z2 (0..12), C = |world X|.  The source projection is greater than
; 1.0 here, so bank 10 holds exact rows instead of the old 255/256 clamp.
; Result: E = projected magnitude, saturated to the off-screen value 255.
_monosh_projection_near_direct:
    ; RODATA_10 no longer necessarily begins at $8000: banked upload code may
    ; precede it.  Add the complete linked base instead of silently indexing
    ; whatever happens to occupy $80xx; this also handles a non-page-aligned
    ; table without padding the ROM bank.
    ld h,a
    ld l,c
    ld de,_monosh_projection_near_rows
    add hl,de
    di
    ld a,10
    ld ($7000),a
    ld e,(hl)
    ld a,3
    ld ($7000),a
    ei
    ret
