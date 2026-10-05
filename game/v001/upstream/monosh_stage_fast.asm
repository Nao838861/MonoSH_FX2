SECTION CODE_3

PUBLIC _monosh_stage_fast_update_positions
PUBLIC _monosh_stage_fast_render
PUBLIC _monosh_stage_fast_update
PUBLIC _monosh_stage_fast_check_player_bullets
PUBLIC _monosh_stage_fast_select_collision_bullet
PUBLIC _monosh_stage_frame
PUBLIC monosh_stage_fast_asset
PUBLIC monosh_stage_fast_width
PUBLIC monosh_stage_fast_height
PUBLIC monosh_stage_fast_half_width
PUBLIC monosh_stage_fast_center
PUBLIC monosh_stage_fast_bottom

EXTERN _monosh_stage_objects
EXTERN _monosh_stage_object_count
EXTERN _monosh_stage_spawn_index
EXTERN _monosh_stage_frame_counter
EXTERN _monosh_stage_spawn_wait
EXTERN _monosh_stage_half_frame
EXTERN _monosh_stage_near_count
EXTERN _monosh_stage_hitboxes
EXTERN _monosh_stage_hitbox_count
EXTERN _monosh_stage_need_hitboxes
EXTERN _monosh_player_x
EXTERN _monosh_player_bottom
EXTERN _monosh_stage_contact_result
EXTERN _monosh_stage1_spawns
EXTERN _stage_bush0_geometry
EXTERN _stage_bush1_geometry
EXTERN _stage_flystone_geometry
EXTERN _stage_em0_geometry
EXTERN _stage_tree0_geometry
EXTERN _stage_bom0_geometry
EXTERN _monosh_stage_lift
EXTERN _monosh_ground_screen_delta
EXTERN _monosh_ground_depth_pointer
EXTERN _monosh_ground_depth_select
EXTERN _monosh_ground_offset
EXTERN _monosh_projection_scale
EXTERN _monosh_projection_high_rows
EXTERN _monosh_projection_direct
EXTERN _monosh_projection_near_direct
EXTERN _mode3_attribute_count
EXTERN _monosh_player_bullets
EXTERN _monosh_player_bullet_count
EXTERN _monosh_runtime_frame_counter
EXTERN _monosh_collision_bullet_bands
EXTERN _monosh_collision_band_bits
EXTERN _monosh_collision_min_x
EXTERN _monosh_collision_max_x
EXTERN _monosh_stage_collision_bullet_cursor
EXTERN _monosh_stage_collision_bullet_index
EXTERN _mode3_fast_emit_stage
EXTERN _mode3_depth_reserve
EXTERN _mode3_depth_reserve_clobber
EXTERN _v9968_ground_stripes_pump_clobber

; Complete bank-local Stage frame.  Preserve the C ordering exactly while
; avoiding two wrapper calls and z88dk's 16-bit boolean temporaries.
_monosh_stage_frame:
    ld hl,(_monosh_player_x)
    call _monosh_stage_fast_update
    ld a,(_monosh_player_bullet_count)
    or a
    jr z,monosh_stage_frame_collision_none
    ld a,(_monosh_runtime_frame_counter)
    and 1
    jr monosh_stage_frame_collision_ready
monosh_stage_frame_collision_none:
    xor a
monosh_stage_frame_collision_ready:
    ld (_monosh_stage_need_hitboxes),a
monosh_stage_frame_render:
    call _monosh_stage_fast_render
    ld a,(_monosh_stage_contact_result)
    ld l,a
    ld h,0
    ret

; void monosh_stage_fast_update_positions(signed char camera_step)
;     __z88dk_fastcall
; StageObject: world_x(2), depth2, type, fall_level, timer (6 bytes).
_monosh_stage_fast_update_positions:
    push ix
    xor a
    ld (_monosh_stage_near_count),a
    ld c,l                         ; constant for the complete object pass
    ld ix,_monosh_stage_objects
    ld a,(_monosh_stage_object_count)
    or a
    jp z,monosh_stage_fast_update_done
    ld b,a

monosh_stage_fast_update_loop:
    ; Explosions keep advancing toward the camera during their visible
    ; lifetime; only their collision participation changes.
    ld a,(ix+3)
    cp 2
    jr nz,monosh_stage_fast_normal_depth
    ld a,(ix+5)
    or a
    jr z,monosh_stage_fast_remove
    dec a
    ld (ix+5),a
    ld a,(ix+4)
    or a
    jr z,monosh_stage_fast_bom_stored
    dec a
    ld (ix+4),a
monosh_stage_fast_bom_stored:
    ld a,(ix+2)
    cp 3
    jr c,monosh_stage_fast_remove
    jr monosh_stage_fast_advance_depth

monosh_stage_fast_normal_depth:
    ld a,(ix+2)
    or a
    jr z,monosh_stage_fast_remove

monosh_stage_fast_advance_depth:
    dec a
    ld (ix+2),a
    or a
    jr nz,monosh_stage_fast_not_near
    ld a,1
    ld (_monosh_stage_near_count),a
monosh_stage_fast_not_near:
    ld a,c
    or a
    jr z,monosh_stage_fast_position_advance
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,a
    ld d,0
    bit 7,e
    jr z,monosh_stage_fast_step_ready
    dec d
monosh_stage_fast_step_ready:
    or a
    sbc hl,de
    ld (ix+0),l
    ld (ix+1),h
monosh_stage_fast_position_advance:
    ld de,6
    add ix,de
    djnz monosh_stage_fast_update_loop
    jr monosh_stage_fast_update_done

monosh_stage_fast_remove:
    ld a,(_monosh_stage_object_count)
    dec a
    ld (_monosh_stage_object_count),a
    dec b
    jr z,monosh_stage_fast_update_done

    ; HL = address of the former last object (index * 6).
    ld l,a
    ld h,0
    ld e,l
    ld d,0
    add hl,hl
    add hl,de
    add hl,hl
    ld de,_monosh_stage_objects
    add hl,de
    push ix
    pop de
    push bc
    ld bc,6
    ldir
    pop bc
    ; Forward traversal has not reached the former last slot yet.  Process
    ; its replacement at the current address before advancing IX.
    jp monosh_stage_fast_update_loop

monosh_stage_fast_update_done:
    pop ix
    ret

; Stage object types are a closed 0..7 set.  Keep the mode-3 asset and direct
; geometry pointer in one four-byte record.  The former path first indexed an
; asset map and then indexed a second pointer table, although both choices
; are invariant for the object's type.
monosh_stage_fast_type_records:
    defb 5
    defw _stage_bom0_geometry
    defb 0
    defb 4
    defw _stage_tree0_geometry
    defb 0
    defb 5
    defw _stage_bom0_geometry
    defb 0
    defb 0
    defw _stage_bush0_geometry
    defb 0
    defb 2
    defw _stage_flystone_geometry
    defb 0
    defb 3
    defw _stage_em0_geometry
    defb 0
    defb 5
    defw _stage_bom0_geometry
    defb 0
    defb 1
    defw _stage_bush1_geometry
    defb 0

; void monosh_stage_fast_update(signed int player_screen_x) __z88dk_fastcall
_monosh_stage_fast_update:
    push ix
    push iy
    ld a,(_monosh_stage_half_frame)
    xor 1
    ld (_monosh_stage_half_frame),a
    ld c,a
    ; Centred play is the common unattended and keyboard-neutral case.  Its
    ; camera step is exactly zero on both interpolation fields.
    ld a,h
    or a
    jr nz,monosh_stage_fast_camera_general
    ld a,l
    cp 128
    jr nz,monosh_stage_fast_camera_general
    xor a
    ld (monosh_stage_fast_camera_step),a
    jp monosh_stage_fast_spawn_phase
monosh_stage_fast_camera_general:
    ld de,-128
    add hl,de
    sra h
    rr l
    sra h
    rr l
    sra h
    rr l
    sra h
    rr l
    ; The source subtracts (player_x >> 4) once per 30 Hz logic update.
    ; Z2 legitimately advances once per 60 Hz field, but applying the full X
    ; camera step on both fields doubled the lateral scroll.  Split signed
    ; odd steps as 3+4 / -3+-4 so the two-field total remains exact.
    ld a,c
    rlca
    rlca
    rlca
    rlca
    ld e,a
    ld a,l
    and $0f
    or e
    ld e,a
    ld d,0
    ld hl,monosh_stage_fast_camera_half_step
    add hl,de
    ld a,(hl)
    ld (monosh_stage_fast_camera_step),a

monosh_stage_fast_spawn_phase:
    ld hl,(_monosh_stage_frame_counter)
    inc hl
    ld (_monosh_stage_frame_counter),hl
    ld hl,(_monosh_stage_spawn_wait)
    ld a,h
    or l
    jr z,monosh_stage_fast_spawn_loop
    dec hl
    ld (_monosh_stage_spawn_wait),hl
    jp monosh_stage_fast_update_done_no_positions

monosh_stage_fast_spawn_loop:
    ld a,(_monosh_stage_spawn_index)
    ld e,a
    ld d,0
    ld l,a
    ld h,0
    add hl,hl
    add hl,de
    add hl,hl
    ld de,_monosh_stage1_spawns
    add hl,de
    push hl
    pop ix

    ld e,(ix+0)
    ld d,(ix+1)
    ld hl,(_monosh_stage_frame_counter)
    or a
    sbc hl,de
    jr c,monosh_stage_fast_spawn_future
    ld a,(ix+2)
    cp $ff
    jr z,monosh_stage_fast_spawn_complete

    ld a,(_monosh_stage_object_count)
    cp 16
    jr nc,monosh_stage_fast_spawn_advance
    ld l,a
    ld h,0
    ld e,l
    ld d,0
    add hl,hl
    add hl,de
    add hl,hl
    ld de,_monosh_stage_objects
    add hl,de
    push hl
    pop iy
    ld a,(ix+3)
    ld (iy+0),a
    ld a,(ix+4)
    ld (iy+1),a
    ld (iy+2),110
    ld a,(ix+2)
    ld (iy+3),a
    ld a,(ix+5)
    ld (iy+4),a
    xor a
    ld (iy+5),a
    ld a,(_monosh_stage_object_count)
    inc a
    ld (_monosh_stage_object_count),a

monosh_stage_fast_spawn_advance:
    ld a,(_monosh_stage_spawn_index)
    inc a
    ld (_monosh_stage_spawn_index),a
    jr monosh_stage_fast_spawn_loop

monosh_stage_fast_spawn_future:
    ; DE is the future entry frame.  Store (entry-current-1), because the
    ; next field is counted when this routine is entered again.
    ld hl,(_monosh_stage_frame_counter)
    ex de,hl
    or a
    sbc hl,de
    dec hl
    ld (_monosh_stage_spawn_wait),hl
    jr monosh_stage_fast_update_done_no_positions

monosh_stage_fast_spawn_complete:
    ; Hold cheaply at the terminator until the enemy timeline starts the
    ; boss.  The stage is restarted long before this 16-bit value can wrap.
    ld hl,$ffff
    ld (_monosh_stage_spawn_wait),hl

monosh_stage_fast_update_done_no_positions:
    ld a,(monosh_stage_fast_camera_step)
    ld l,a
    ld h,0
    bit 7,l
    jr z,monosh_stage_fast_update_call
    dec h
monosh_stage_fast_update_call:
    call _monosh_stage_fast_update_positions
    pop iy
    pop ix
    ret

_monosh_stage_fast_render:
    push ix
    push iy
    xor a
    ld (_monosh_stage_contact_result),a
    ld a,(_mode3_attribute_count)
    ld (monosh_stage_fast_attribute_count),a
    ld a,(_monosh_stage_need_hitboxes)
    or a
    jr z,monosh_stage_fast_buckets_ready
    xor a
    ld (_monosh_stage_hitbox_count),a
monosh_stage_fast_buckets_ready:
    ld a,(_monosh_stage_object_count)
    or a
    jr z,monosh_stage_fast_depth_row_ready
    ld a,(_monosh_ground_offset)
    call _monosh_ground_depth_select
    ld a,(_monosh_stage_object_count)
monosh_stage_fast_depth_row_ready:
    ld b,a
    ld ix,_monosh_stage_objects
    or a
    jp z,monosh_stage_fast_render_done
    dec a
    jr z,monosh_stage_fast_render_loop
    ; Dense AoS index * 6 in constant time.  The former repeated IX advance
    ; grew linearly with the busiest six-to-sixteen-object formations.
    ld l,a
    ld h,0
    ld e,a
    ld d,0
    add hl,hl                      ; 2n
    add hl,de                      ; 3n
    add hl,hl                      ; 6n
    ld de,_monosh_stage_objects
    add hl,de
    push hl
    pop ix

monosh_stage_fast_render_loop:
    ; The IM2 handler deliberately uses the alternate register set as its
    ; workspace, so live loop state cannot be kept in B'/C'.
    push bc
    ld a,(ix+2)
    ld (monosh_stage_fast_z),a

    ; Map the closed Stage 1 type set directly to its mode-3 asset number.
    ld a,(ix+3)
    ld (monosh_stage_fast_type),a
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    ld de,monosh_stage_fast_type_records
    add hl,de
    ld a,(hl)
    ld (monosh_stage_fast_asset),a
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,(monosh_stage_fast_z)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (monosh_stage_fast_width),de
    inc hl
    ld a,(hl)
    ld (monosh_stage_fast_bottom),a
    inc hl
    ld a,(hl)
    ld (monosh_stage_fast_half_width),a

    ; magnitude = projection[z][abs(world_x)].  Keep sign/high distance in
    ; B/D across the fixed-bank table call.  The former scratch stores and
    ; reloads cost six absolute memory accesses for every visible object.
    ld l,(ix+0)
    ld h,(ix+1)
    xor a
    ld b,a                         ; B=0 positive, B=1 negative
    bit 7,h
    jr z,monosh_stage_fast_abs_ready
    inc a
    ld b,a
    xor a
    sub l
    ld l,a
    ld a,0                    ; keep the borrow from the low-byte negate
    sbc a,h
    ld h,a
monosh_stage_fast_abs_ready:
    ; Near Z uses exact >1.0 rows.  Far objects can remain visible beyond
    ; |world X|=511, so retain enough high-byte range for their projected
    ; sprite edge to leave the viewport naturally.
    ld a,h
    cp 7
    jp nc,monosh_stage_fast_render_next
    ld d,a                         ; high byte of absolute world X
    ld c,l
    ld a,(monosh_stage_fast_z)
    cp 13
    jr nc,monosh_stage_fast_projection_table
    ld a,d
    or a
    jp nz,monosh_stage_fast_render_next
    ld a,(monosh_stage_fast_z)
    call _monosh_projection_near_direct
    jr monosh_stage_fast_magnitude_ready
monosh_stage_fast_projection_table:
    cp 14
    jr nc,monosh_stage_fast_projection_far
    ; Z2 13 is exactly 255/256.  A high-byte distance cannot remain visible
    ; at this scale; the low-byte result is distance-1 except at zero.
    ld a,d
    or a
    jp nz,monosh_stage_fast_render_next
    ld a,c
    or a
    ld e,a
    jr z,monosh_stage_fast_magnitude_ready
    dec e
    jr monosh_stage_fast_magnitude_ready
monosh_stage_fast_projection_far:
    ld a,(monosh_stage_fast_z)
    call _monosh_projection_direct
    ld c,e
    ld a,d
    or a
    jr nz,monosh_stage_fast_projection_high
    ld e,c
    jr monosh_stage_fast_magnitude_ready
monosh_stage_fast_projection_high:
    ld a,d
    add a,+((_monosh_projection_high_rows % 65536) / 256)
    ld h,a
    ld a,(monosh_stage_fast_z)
    ld l,a
    ld a,(hl)
    add a,c
    jp c,monosh_stage_fast_render_next
    ld e,a

monosh_stage_fast_magnitude_ready:

    ld a,b
    or a
    jr nz,monosh_stage_fast_center_negative
    ld l,e
    ld h,0
    ld a,l
    add a,128
    ld l,a
    ld a,h
    adc a,0
    ld h,a
    jr monosh_stage_fast_center_ready
monosh_stage_fast_center_negative:
    ld a,128
    sub e
    ld l,a
    ld a,0
    sbc a,0
    ld h,a
monosh_stage_fast_center_ready:
    ld (monosh_stage_fast_center),hl

    ; Reject horizontally invisible objects before doing camera-row Y
    ; projection, ground sinking and airborne lift.  The previous ordering
    ; paid that entire path for objects already outside the side edges.
    ld a,(monosh_stage_fast_half_width)
    ld e,a
    ld d,0
    push hl
    add hl,de
    bit 7,h
    pop hl
    jp nz,monosh_stage_fast_render_next
    or a
    sbc hl,de
    ld a,h
    or a
    jr z,monosh_stage_fast_horizontal_visible
    cp $ff
    jp nz,monosh_stage_fast_render_next
monosh_stage_fast_horizontal_visible:

    ; Reproject the source distance from its lower vanishing point through
    ; the current camera row.  MonoSH used a depth-dependent table here; the
    ; former uniform screen delta pushed near bushes below the display and
    ; forced trees onto an artificial Y=201 ledge.  The -12 converts the
    ; source 224-line field to this 212-line playfield (219 -> 207).
    ld a,(monosh_stage_fast_bottom)
    ld e,a
    ld a,219
    sub e
    ld e,a
    ld d,0
    ld hl,(_monosh_ground_depth_pointer)
    add hl,de
    ld a,(hl)
    ld e,a
    ld a,207
    sub e
    ld (monosh_stage_fast_bottom),a
    xor a
    ld (monosh_stage_fast_bottom+1),a

    ; Bushes and trees use a cropped source whose last opaque row can round
    ; above the bitmap ground edge after strong perspective reduction.  Sink
    ; only those ground assets by 0..3 pixels.  The former Z/32 thresholds
    ; changed while the projected root was stationary, making the object
    ; visibly step backwards.  Defer the three one-pixel reductions until the
    ; near-depth root steps are large enough to absorb them at every camera
    ; height, while retaining the same near/far correction.
    ld a,(monosh_stage_fast_asset)
    cp 2
    jr c,monosh_stage_fast_apply_ground_sink
    cp 4
    jr nz,monosh_stage_fast_ground_sink_done
monosh_stage_fast_apply_ground_sink:
    ld a,(monosh_stage_fast_z)
    ld e,3
    cp 9
    jr nc,monosh_stage_fast_ground_sink_ready
    dec e
    cp 6
    jr nc,monosh_stage_fast_ground_sink_ready
    dec e
    cp 2
    jr nc,monosh_stage_fast_ground_sink_ready
    dec e
monosh_stage_fast_ground_sink_ready:
    ld a,(monosh_stage_fast_bottom)
    add a,e
    ld (monosh_stage_fast_bottom),a
monosh_stage_fast_ground_sink_done:

    ; Apply the fixed FlyStone/explosion lift to the table-projected bottom.
    ld a,(monosh_stage_fast_type)
    cp 4
    jr z,monosh_stage_fast_full_lift
    cp 2
    jr nz,monosh_stage_fast_bottom_ready
    ld a,(ix+4)
    or a
    jr z,monosh_stage_fast_bottom_ready
    cp 13
    jr c,monosh_stage_fast_lift_level_ready
    ld a,12
    jr monosh_stage_fast_lift_level_ready
monosh_stage_fast_full_lift:
    ld a,12
monosh_stage_fast_lift_level_ready:
    ld (monosh_stage_fast_lift_level),a
    and 1
    ld (monosh_stage_fast_lift_odd),a
    ld a,(monosh_stage_fast_lift_level)
    srl a
    add a,a
    ld e,a
    ld d,0
    ld hl,_monosh_stage_lift
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,(monosh_stage_fast_z)
    ld l,a
    ld h,0
    add hl,de
    ld e,(hl)
    ld a,(monosh_stage_fast_lift_odd)
    or a
    jr z,monosh_stage_fast_lift_value_ready
    ld a,(monosh_stage_fast_lift_level)
    srl a
    inc a
    add a,a
    ld l,a
    ld h,0
    ld bc,_monosh_stage_lift
    add hl,bc
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld a,(monosh_stage_fast_z)
    ld l,a
    ld h,0
    add hl,bc
    ld a,(hl)
    add a,e
    inc a
    srl a
    ld e,a
monosh_stage_fast_lift_value_ready:
    ld d,0
monosh_stage_fast_apply_lift:
    ld a,(monosh_stage_fast_bottom)
    sub e
    ld (monosh_stage_fast_bottom),a
    ld a,(monosh_stage_fast_bottom+1)
    sbc a,0
    ld (monosh_stage_fast_bottom+1),a
monosh_stage_fast_bottom_ready:

    ; Ground-anchored Bush/Tree/EM0 geometry is always vertically visible for
    ; every legal camera offset.  Only airborne FlyStone and its falling
    ; explosion can leave the 212-line window.
    ld a,(monosh_stage_fast_type)
    cp 4
    jr z,monosh_stage_fast_check_vertical
    cp 2
    jr nz,monosh_stage_fast_queue
monosh_stage_fast_check_vertical:
    ; Vertical visibility: bottom > 0 and top < 212.
    ld a,(monosh_stage_fast_bottom+1)
    or a
    jp nz,monosh_stage_fast_render_next
    ld a,(monosh_stage_fast_bottom)
    or a
    jp z,monosh_stage_fast_render_next
    ld l,a
    ld h,0
    ld a,(monosh_stage_fast_height)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    bit 7,h
    jr nz,monosh_stage_fast_queue
    ld a,l
    cp 212
    jp nc,monosh_stage_fast_render_next

monosh_stage_fast_queue:
    ; Contact uses the exact projected rectangle already live in this pass.
    ; The former ROM path returned to C, walked all objects again and repeated
    ; projection for the single Z=0 candidate.
    ld a,(monosh_stage_fast_z)
    or a
    jp nz,monosh_stage_fast_queue_collision
    ld a,(monosh_stage_fast_type)
    cp 1
    jr z,monosh_stage_fast_contact_tree
    cp 4
    jr z,monosh_stage_fast_contact_flystone
    cp 3
    jr z,monosh_stage_fast_contact_bush0
    cp 7
    jp nz,monosh_stage_fast_queue_collision
    ld e,74
    ld d,2
    jr monosh_stage_fast_contact_bush_height
monosh_stage_fast_contact_bush0:
    ld e,54
    ld d,2
monosh_stage_fast_contact_bush_height:
    ld a,(_monosh_player_bottom)
    cp 196
    jp c,monosh_stage_fast_queue_collision
    jr monosh_stage_fast_contact_radius_ready
monosh_stage_fast_contact_tree:
    ld e,36
    ld d,1
    jr monosh_stage_fast_contact_radius_ready
monosh_stage_fast_contact_flystone:
    ld e,32
    ld d,1
monosh_stage_fast_contact_radius_ready:
    ld a,d
    ld (monosh_stage_fast_contact_kind),a
    ; The source-equivalent Z=0 contact centre deliberately uses 128+worldX,
    ; not the >1.0 visual projection used by the enlarged near sprite.
    push de                         ; radius/result
    ld l,(ix+0)
    ld h,(ix+1)
    ld de,128
    add hl,de
    ld de,(_monosh_player_x)
    or a
    sbc hl,de
    bit 7,h
    jr z,monosh_stage_fast_contact_dx_ready
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
monosh_stage_fast_contact_dx_ready:
    pop de
    ld a,h
    or a
    jp nz,monosh_stage_fast_queue_collision
    ld a,e
    cp l
    jp c,monosh_stage_fast_queue_collision
    ; bottom >= playerBottom-40.
    ld a,(_monosh_player_bottom)
    sub 40
    ld e,a
    ld a,(monosh_stage_fast_bottom)
    cp e
    jp c,monosh_stage_fast_queue_collision
    ; top <= playerBottom+8.  Negative tops always pass.
    ld l,a
    ld h,0
    ld a,(monosh_stage_fast_height)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    bit 7,h
    jr nz,monosh_stage_fast_contact_hit
    ld a,h
    or a
    jp nz,monosh_stage_fast_queue_collision
    ld a,(_monosh_player_bottom)
    add a,8
    cp l
    jp c,monosh_stage_fast_queue_collision
monosh_stage_fast_contact_hit:
    ld a,(monosh_stage_fast_contact_kind)
    ld (_monosh_stage_contact_result),a

monosh_stage_fast_queue_collision:
    ld a,(_monosh_stage_need_hitboxes)
    or a
    jp z,monosh_stage_fast_hitbox_done
    ; Explosions cannot be hit.  Like the NES collision buckets, link only
    ; collidable object types instead of filtering explosions during probes.
    ld a,(monosh_stage_fast_type)
    cp 2
    jp z,monosh_stage_fast_hitbox_done
    call monosh_stage_fast_collide_current

monosh_stage_fast_hitbox_done:
    ; Allocate directly in the backwards-growing Z-band stack.  This removes
    ; both per-object sort descriptors and scattered VRAM reads at commit.
    ld a,(monosh_stage_fast_attribute_count)
    ld e,a
    ld a,(monosh_stage_fast_width)
    cp 17
    ld b,1
    jr c,monosh_stage_fast_reserve_capacity
    inc b
monosh_stage_fast_reserve_capacity:
    ld a,e
    add a,b
    cp 65
    jp nc,monosh_stage_fast_render_next
    ; A already is the post-reservation global plane count.  Publish it once
    ; here instead of recomputing it at the end of every emitter.
    ld (monosh_stage_fast_attribute_count),a
    ld a,(monosh_stage_fast_z)
    rrca
    rrca
    rrca
    rrca
    and 7
    call _mode3_depth_reserve_clobber
    push hl
    jp monosh_stage_fast_emit_attributes
monosh_stage_fast_emit_done:
monosh_stage_fast_register_done:

monosh_stage_fast_render_next:
    ; Enemy/player preparation has already supplied several asynchronous VDP
    ; polls before Stage rendering begins.  Joining at frame end remains the
    ; correctness boundary; avoid six usually-inactive CE probes here.
    pop bc
    ld de,-6
    add ix,de
    djnz monosh_stage_fast_render_continue
    jr monosh_stage_fast_render_done
monosh_stage_fast_render_continue:
    jp monosh_stage_fast_render_loop

monosh_stage_fast_render_done:
    ld a,(monosh_stage_fast_attribute_count)
    ld (_mode3_attribute_count),a
    pop iy
    pop ix
    ret

; Emit the already projected Stage 1 object directly at the live IY cursor.
; All six assets use page/palette zero.  Only the tree uses SZ=2/3 instead
; of SZ=0/1; its non-contiguous right pattern is handled explicitly.
monosh_stage_fast_emit_attributes:
    ; The caller has already reserved one/two planes and checked the global
    ; 64-plane limit.
    ; Bush0/Bush1/FlyStone/EM0 share page 0 and the same SZ=0/1 layout.
    ; Keep their overwhelmingly common path free of the repeated Tree/Bom
    ; tests and dynamic page loads needed by the two exceptional assets.
    ld a,(monosh_stage_fast_asset)
    cp 4
    jp c,monosh_stage_fast_emit_normal
    jp z,monosh_stage_fast_emit_tree
    ; Explosion emitters use IY displacement stores.  Normal/tree emitters
    ; retain the destination on the stack and consume it as a linear HL cursor.
    pop iy
    ; The clobber allocator keeps B at the requested one/two-plane count.
    djnz monosh_stage_fast_emit_explosion_wide
    jr monosh_stage_fast_emit_explosion_small
monosh_stage_fast_emit_explosion_wide:
    jp monosh_stage_fast_emit_wide_direct
monosh_stage_fast_emit_explosion_small:

    ; Small Stage objects are written straight through the live IY cursor.
    ; The old helper chain stored every intermediate in BSS, reloaded it in
    ; three subroutines, and then maintained a second output pointer.  At six
    ; objects that bookkeeping alone consumed almost a full 60 Hz millisecond.
    call monosh_stage_fast_select_patterns
    ld a,(monosh_stage_fast_bottom)
    ld e,a
    ld a,(monosh_stage_fast_height)
    ld d,a
    ld a,e
    sub d
    ld (iy+0),a
    ld a,0
    sbc a,0
    and 3
    ld (iy+1),a
    ld a,(monosh_stage_fast_height)
    ld (iy+2),a
    xor a
    ld (iy+3),a
    ld hl,(monosh_stage_fast_center)
    ld a,(monosh_stage_fast_half_width)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ld (iy+4),l
    ld a,h
    and 3
    ld e,a
    ld a,(monosh_stage_fast_plane_page)
    or e
    ld (iy+5),a
    ld a,(monosh_stage_fast_width)
    ld (iy+6),a
    ld a,(monosh_stage_fast_pattern_small)
    ld (iy+7),a
    jp monosh_stage_fast_emit_done

monosh_stage_fast_emit_normal:
    djnz monosh_stage_fast_emit_normal_wide

    ; Keep the common top-left coordinates in BC/DE, then stream the whole
    ; attribute record through HL.  A linear (HL) store is much cheaper than
    ; an IY displacement store on the Z80 and the arena is contiguous.
    ld a,(monosh_stage_fast_bottom)
    ld e,a
    ld a,(monosh_stage_fast_height)
    ld d,a
    ld a,e
    sub d
    ld c,a
    ld a,0
    sbc a,0
    ld b,a
    ld hl,(monosh_stage_fast_center)
    ld a,(monosh_stage_fast_half_width)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ex de,hl

    pop hl                         ; destination saved by the caller
    ld (hl),c
    inc hl
    ld a,b
    and 3
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_width)
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_asset)
    ld e,a
    add a,a
    add a,e
    add a,2
    ld (hl),a
    jp monosh_stage_fast_emit_done

monosh_stage_fast_emit_normal_wide:
    ld a,(monosh_stage_fast_asset)
    ld e,a
    add a,a
    add a,e
    add a,3
    ld (monosh_stage_fast_pattern_left),a

    ld a,(monosh_stage_fast_bottom)
    ld e,a
    ld a,(monosh_stage_fast_height)
    ld d,a
    ld a,e
    sub d
    ld c,a
    ld a,0
    sbc a,0
    ld b,a
    ld hl,(monosh_stage_fast_center)
    ld a,(monosh_stage_fast_half_width)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ex de,hl

    pop hl                         ; destination saved by the caller
    ld (hl),c
    inc hl
    ld a,b
    and 3
    or $40
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_half_width)
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_pattern_left)
    ld (hl),a
    inc hl

    ld (hl),c
    inc hl
    ld a,b
    and 3
    or $40
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld de,(monosh_stage_fast_center)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_width)
    ld e,a
    ld a,(monosh_stage_fast_half_width)
    ld d,a
    ld a,e
    sub d
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_pattern_left)
    inc a
    ld (hl),a
    jp monosh_stage_fast_emit_done

; Tree uses the same fixed page-0 layout as normal Stage assets but its
; source planes are 16x64 (SZ=2) / 32x64 (SZ=3) and its right-half pattern
; is non-contiguous.  Keeping a direct linear template avoids routing every
; tree through the dynamic explosion/page selector.
monosh_stage_fast_emit_tree:
    djnz monosh_stage_fast_emit_tree_wide

    ld a,(monosh_stage_fast_bottom)
    ld e,a
    ld a,(monosh_stage_fast_height)
    ld d,a
    ld a,e
    sub d
    ld c,a
    ld a,0
    sbc a,0
    ld b,a
    ld hl,(monosh_stage_fast_center)
    ld a,(monosh_stage_fast_half_width)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ex de,hl
    pop hl                         ; destination saved by the caller
    ld (hl),c
    inc hl
    ld a,b
    and 3
    or $80
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_width)
    ld (hl),a
    inc hl
    ld (hl),$0e
    jp monosh_stage_fast_emit_done

monosh_stage_fast_emit_tree_wide:
    ld a,(monosh_stage_fast_bottom)
    ld e,a
    ld a,(monosh_stage_fast_height)
    ld d,a
    ld a,e
    sub d
    ld c,a
    ld a,0
    sbc a,0
    ld b,a
    ld hl,(monosh_stage_fast_center)
    ld a,(monosh_stage_fast_half_width)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ex de,hl
    pop hl                         ; destination saved by the caller
    ld (hl),c
    inc hl
    ld a,b
    and 3
    or $c0
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_half_width)
    ld (hl),a
    inc hl
    ld (hl),$0f
    inc hl

    ld (hl),c
    inc hl
    ld a,b
    and 3
    or $c0
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_height)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld de,(monosh_stage_fast_center)
    ld (hl),e
    inc hl
    ld a,d
    and 3
    ld (hl),a
    inc hl
    ld a,(monosh_stage_fast_width)
    ld e,a
    ld a,(monosh_stage_fast_half_width)
    ld d,a
    ld a,e
    sub d
    ld (hl),a
    inc hl
    ld (hl),$80
    jp monosh_stage_fast_emit_done

monosh_stage_fast_emit_wide_direct:
    call monosh_stage_fast_select_patterns

    ; Both halves share top, vertical scale, height and flags.  Calculate
    ; them once and duplicate four bytes directly, then fill only X/width/
    ; pattern for each half.  IY remains the sole output cursor.
    ld a,(monosh_stage_fast_bottom)
    ld e,a
    ld a,(monosh_stage_fast_height)
    ld d,a
    ld a,e
    sub d
    ld (iy+0),a
    ld a,0
    sbc a,0
    and 3
    or $40                        ; wide SZ=1
    ld (iy+1),a
    ld a,(monosh_stage_fast_height)
    ld (iy+2),a
    xor a
    ld (iy+3),a
    ld hl,(monosh_stage_fast_center)
    ld a,(monosh_stage_fast_half_width)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ld (iy+4),l
    ld a,h
    and 3
    ld e,a
    ld a,(monosh_stage_fast_plane_page)
    or e
    ld (iy+5),a
    ld a,(monosh_stage_fast_half_width)
    ld (iy+6),a
    ld a,(monosh_stage_fast_pattern_left)
    ld (iy+7),a

    ld a,(iy+0)
    ld (iy+8),a
    ld a,(iy+1)
    ld (iy+9),a
    ld a,(iy+2)
    ld (iy+10),a
    xor a
    ld (iy+11),a
    ld hl,(monosh_stage_fast_center)
    ld (iy+12),l
    ld a,h
    and 3
    ld e,a
    ld a,(monosh_stage_fast_plane_page)
    or e
    ld (iy+13),a
    ld a,(monosh_stage_fast_width)
    ld e,a
    ld a,(monosh_stage_fast_half_width)
    ld d,a
    ld a,e
    sub d
    ld (iy+14),a
    ld a,(monosh_stage_fast_pattern_right)
    ld (iy+15),a
    jp monosh_stage_fast_emit_done

; Select the three source patterns once per object.  Assets 0..3 are
; consecutive triples; tree/explosion cross the pattern-number boundary.
monosh_stage_fast_select_patterns:
    xor a
    ld (monosh_stage_fast_plane_page),a
    ld a,(monosh_stage_fast_asset)
    cp 4
    jr z,monosh_stage_fast_patterns_tree
    cp 5
    jr z,monosh_stage_fast_patterns_bom
    ld e,a
    add a,a
    add a,e
    add a,2
    ld (monosh_stage_fast_pattern_small),a
    inc a
    ld (monosh_stage_fast_pattern_left),a
    inc a
    ld (monosh_stage_fast_pattern_right),a
    ret
monosh_stage_fast_patterns_tree:
    ld a,$0e
    ld (monosh_stage_fast_pattern_small),a
    inc a
    ld (monosh_stage_fast_pattern_left),a
    ld a,$80
    ld (monosh_stage_fast_pattern_right),a
    ret
monosh_stage_fast_patterns_bom:
    ; Use the remaining lifetime as a direct 60 Hz animation clock.  A newly
    ; created explosion starts at frame 0; every frame lasts eight fields.
    ld a,(ix+5)
    ld e,a
    ld d,0
    ld hl,monosh_stage_fast_bom_frame_by_timer
    add hl,de
    ld a,(hl)
    or a
    jr z,monosh_stage_fast_patterns_bom_frame0
    ld e,a
    ld a,$30                    ; page 3 in attribute-byte-5 form
    ld (monosh_stage_fast_plane_page),a
    ld a,e
    add a,a
    add a,e
    add a,$3d                    ; frames 1..3 -> page-3 $40,$43,$46
    jr monosh_stage_fast_patterns_bom_store
monosh_stage_fast_patterns_bom_frame0:
    ld a,$81
monosh_stage_fast_patterns_bom_store:
    ld (monosh_stage_fast_pattern_small),a
    inc a
    ld (monosh_stage_fast_pattern_left),a
    inc a
    ld (monosh_stage_fast_pattern_right),a
    ret

; Resolve all three player-shot slots while the current Stage object's
; projected rectangle is still in the renderer scratch fields.  Rendering
; continues with the pre-hit asset selected above, so the explosion begins
; on the following field exactly as it did with the deferred cache walk.
monosh_stage_fast_collide_current:
    ; Shared inverse Z bucket: one mask was built after projectile motion and
    ; is consumed by both enemy and Stage collision paths this field.
    ld a,(monosh_stage_fast_z)
    rrca
    rrca
    rrca
    rrca
    and 7
    ld e,a
    ld d,0
    ld hl,_monosh_collision_band_bits
    add hl,de
    ld a,(_monosh_collision_bullet_bands)
    and (hl)
    or a
    ret z

    ld a,(monosh_stage_fast_width)
    srl a
    ld (monosh_stage_fast_collision_radius),a
    ld a,(monosh_stage_fast_center+1)
    or a
    jr nz,monosh_stage_fast_collide_envelope_pass
    ld a,(monosh_stage_fast_collision_radius)
    ld e,a
    ld a,(_monosh_collision_min_x)
    sub e
    jr nc,monosh_stage_fast_collide_envelope_left_ready
    xor a
monosh_stage_fast_collide_envelope_left_ready:
    ld e,a
    ld a,(monosh_stage_fast_center)
    cp e
    ret c
    ld a,(monosh_stage_fast_collision_radius)
    ld e,a
    ld a,(_monosh_collision_max_x)
    add a,e
    jr c,monosh_stage_fast_collide_envelope_pass
    ld e,a
    ld a,(monosh_stage_fast_center)
    cp e
    jr z,monosh_stage_fast_collide_envelope_pass
    ret nc
monosh_stage_fast_collide_envelope_pass:

    ; Load each of the fixed three shot slots directly.  B=Y, C=X, D=Z.
    ; This avoids IX/IY displacement loads and the per-slot pointer/counter
    ; loop while retaining the original all-three-shots collision cadence.
    ld a,(_monosh_player_bullets+0)
    cp 1
    jr nz,monosh_stage_fast_collide_slot1
    ld a,(_monosh_player_bullets+2)
    ld b,a
    ld a,(_monosh_player_bullets+1)
    ld c,a
    ld a,(_monosh_player_bullets+3)
    ld d,a
    call monosh_stage_fast_collide_values
    jr c,monosh_stage_fast_collide_hit0
monosh_stage_fast_collide_slot1:
    ld a,(_monosh_player_bullets+5)
    cp 1
    jr nz,monosh_stage_fast_collide_slot2
    ld a,(_monosh_player_bullets+7)
    ld b,a
    ld a,(_monosh_player_bullets+6)
    ld c,a
    ld a,(_monosh_player_bullets+8)
    ld d,a
    call monosh_stage_fast_collide_values
    jr c,monosh_stage_fast_collide_hit1
monosh_stage_fast_collide_slot2:
    ld a,(_monosh_player_bullets+10)
    cp 1
    ret nz
    ld a,(_monosh_player_bullets+12)
    ld b,a
    ld a,(_monosh_player_bullets+11)
    ld c,a
    ld a,(_monosh_player_bullets+13)
    ld d,a
    call monosh_stage_fast_collide_values
    ret nc
    xor a
    ld (_monosh_player_bullets+10),a
    jr monosh_stage_fast_collide_hit
monosh_stage_fast_collide_hit0:
    xor a
    ld (_monosh_player_bullets+0),a
    jr monosh_stage_fast_collide_hit
monosh_stage_fast_collide_hit1:
    xor a
    ld (_monosh_player_bullets+5),a
monosh_stage_fast_collide_hit:
    ld a,(_monosh_player_bullet_count)
    dec a
    ld (_monosh_player_bullet_count),a
    ld a,(ix+3)
    cp 4
    ld (ix+3),2
    ld a,13
    jr z,monosh_stage_fast_inline_fall_ready
    xor a
monosh_stage_fast_inline_fall_ready:
    ld (ix+4),a
    ld (ix+5),49
    ret

; Test one register-packed player shot against the current projected object.
; Carry is set on a hit.  B=shot Y, C=shot X, D=source Z.
monosh_stage_fast_collide_values:
    ld a,d
    add a,a
    ld e,a
    ld a,(monosh_stage_fast_z)
    sub e
    ; NES swept Z interval, converted from source Z to Z2.
    add a,8
    cp 10
    jr nc,monosh_stage_fast_collide_values_miss

    ld a,(monosh_stage_fast_center+1)
    or a
    jr nz,monosh_stage_fast_collide_values_x_signed
    ld a,(monosh_stage_fast_center)
    ld e,a
    ld a,c
    cp e
    jr nc,monosh_stage_fast_collide_values_x_right
    ld a,e
    sub c
    jr monosh_stage_fast_collide_values_x_ready
monosh_stage_fast_collide_values_x_right:
    sub e
monosh_stage_fast_collide_values_x_ready:
    ld l,a
    jr monosh_stage_fast_collide_values_width
monosh_stage_fast_collide_values_x_signed:
    ld hl,(monosh_stage_fast_center)
    ld e,c
    ld d,0
    or a
    sbc hl,de
    bit 7,h
    jr z,monosh_stage_fast_collide_values_x_positive
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
monosh_stage_fast_collide_values_x_positive:
    ld a,h
    or a
    jr nz,monosh_stage_fast_collide_values_miss
monosh_stage_fast_collide_values_width:
    ld a,(monosh_stage_fast_collision_radius)
    cp l
    jr c,monosh_stage_fast_collide_values_miss

    ; Point shot against the visible vertical interval (NES semantics).
    ld a,(monosh_stage_fast_bottom)
    cp b
    jr c,monosh_stage_fast_collide_values_miss
    ld a,(monosh_stage_fast_bottom)
    ld e,a
    ld a,(monosh_stage_fast_height)
    ld d,a
    ld a,e
    sub d
    jr c,monosh_stage_fast_collide_values_miss
    ld e,a
    ld a,b
    cp e
    jr c,monosh_stage_fast_collide_values_miss
monosh_stage_fast_collide_values_hit:
    scf
    ret
monosh_stage_fast_collide_values_miss:
    or a
    ret

; Pick one live player shot in round-robin order.  Return HL=1 when selected.
; Phases 0,1,3 probe one shot each.  New volleys build their broad phase
; immediately, so all three shots retain a <= four-field cadence.
_monosh_stage_fast_select_collision_bullet:
    ld a,(_monosh_player_bullet_count)
    or a
    jr z,monosh_stage_fast_select_collision_none
    push ix
    ld a,(_monosh_stage_collision_bullet_cursor)
    ld b,3
monosh_stage_fast_select_collision_loop:
    cp 3
    jr c,monosh_stage_fast_select_collision_index_ready
    xor a
monosh_stage_fast_select_collision_index_ready:
    ld c,a
    inc a
    cp 3
    jr c,monosh_stage_fast_select_collision_next_ready
    xor a
monosh_stage_fast_select_collision_next_ready:
    ld (_monosh_stage_collision_bullet_cursor),a
    ld a,c
    ld e,a
    add a,a
    add a,a
    add a,e
    ld e,a
    ld d,0
    ld ix,_monosh_player_bullets
    add ix,de
    ld a,(ix+0)
    or a
    jr nz,monosh_stage_fast_select_collision_found
    ld a,(_monosh_stage_collision_bullet_cursor)
    djnz monosh_stage_fast_select_collision_loop
    pop ix
monosh_stage_fast_select_collision_none:
    ld hl,0
    ret
monosh_stage_fast_select_collision_found:
    ld a,c
    ld (_monosh_stage_collision_bullet_index),a
    pop ix
    ld hl,1
    ret

; Player-shot collision against the renderer-built Z broad phase.
_monosh_stage_fast_check_player_bullets:
    push ix
    push iy
    ld a,(_monosh_player_bullet_count)
    or a
    jp z,monosh_stage_fast_collision_done
    ld a,(_monosh_stage_hitbox_count)
    or a
    jp z,monosh_stage_fast_collision_done
    ld a,(_monosh_stage_collision_bullet_index)
    ld e,a
    add a,a
    add a,a
    add a,e
    ld e,a
    ld d,0
    ld ix,_monosh_player_bullets
    add ix,de

monosh_stage_fast_collision_bullet_loop:
    ld a,(ix+0)
    or a
    jp z,monosh_stage_fast_collision_next_bullet

    ; The renderer retained only hitboxes inside this shot's swept Z range.
    ; With at most sixteen Stage objects, a contiguous walk is both
    ; cheaper and more stable than clearing 16 bucket heads, linking every
    ; hitbox, and rebuilding an index into the same tiny cache.
    ld iy,_monosh_stage_hitboxes
    ld a,(_monosh_stage_hitbox_count)
    ld (monosh_stage_fast_collision_hitbox),a

monosh_stage_fast_collision_hitbox_loop:
    ld a,(monosh_stage_fast_collision_hitbox)
    or a
    jp z,monosh_stage_fast_collision_done

    ; A previous selected shot may already have turned this cached object
    ; into an explosion.  Reject the stale entry before doing any geometry.
    ld l,(iy+0)
    ld h,(iy+1)
    ld de,3
    add hl,de
    ld a,(hl)
    cp 2
    jp z,monosh_stage_fast_collision_hitbox_next

    ; The broad phase was rebuilt from current geometry for this shot.
    ld a,(ix+3)
    add a,a
    ld e,a
    ld a,(iy+2)
    sub e
    add a,8
    cp 10
    jp nc,monosh_stage_fast_collision_hitbox_next

    ; Point shot against the visible vertical interval (NES semantics).
    ld a,(iy+7)
    cp (ix+2)
    jp c,monosh_stage_fast_collision_hitbox_next
    ld a,(iy+7)
    sub (iy+4)
    jp c,monosh_stage_fast_collision_hitbox_next
    ld e,a
    ld a,(ix+2)
    cp e
    jp c,monosh_stage_fast_collision_hitbox_next
monosh_stage_fast_collision_top_pass:

    ; Signed 16-bit distance from the cached centre to an unsigned shot X.
    ld l,(iy+5)
    ld h,(iy+6)
    ld e,(ix+1)
    ld d,0
    or a
    sbc hl,de
    bit 7,h
    jr z,monosh_stage_fast_collision_x_positive
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
monosh_stage_fast_collision_x_positive:
    ld a,h
    or a
    jp nz,monosh_stage_fast_collision_hitbox_next
    ld a,(iy+3)
    srl a
    cp l
    jp c,monosh_stage_fast_collision_hitbox_next

    ; Consume the shot and turn its StageObject into a falling explosion.
    xor a
    ld (ix+0),a
    ld a,(_monosh_player_bullet_count)
    dec a
    ld (_monosh_player_bullet_count),a
    ld l,(iy+0)
    ld h,(iy+1)
    inc hl
    inc hl
    inc hl
    ld a,(hl)
    cp 4
    ld (hl),2
    inc hl
    jr nz,monosh_stage_fast_collision_no_fall
    ; Update runs before the first BOM render.  Start at 13 so it becomes
    ; lift level 12 on that field and exactly matches the FlyStone altitude.
    ld a,13
    jr monosh_stage_fast_collision_store_lifetime
monosh_stage_fast_collision_no_fall:
    xor a
monosh_stage_fast_collision_store_lifetime:
    ld (hl),a
    inc hl
    ; Collision is detected after this field's stage render.  The following
    ; update decrements once before the first visible BOM field, so seed 49
    ; to display frame 0 for four complete fields (timer 48..45).
    ld (hl),49
    jp monosh_stage_fast_collision_next_bullet

monosh_stage_fast_collision_hitbox_next:
    ld de,8
    add iy,de
    ld a,(monosh_stage_fast_collision_hitbox)
    dec a
    ld (monosh_stage_fast_collision_hitbox),a
    jp monosh_stage_fast_collision_hitbox_loop

monosh_stage_fast_collision_next_bullet:
    jp monosh_stage_fast_collision_done

monosh_stage_fast_collision_done:
    pop iy
    pop ix
    ret

SECTION RODATA_3

; Indexed by (half_frame << 4) | (signed_step & $0f).  Valid source steps are
; -7..+7.  The two rows sum to the exact source 30 Hz camera displacement.
monosh_stage_fast_camera_half_step:
    defb 0,0,1,1,2,2,3,3,-4,-3,-3,-2,-2,-1,-1,0
    defb 0,1,1,2,2,3,3,4,-4,-4,-3,-3,-2,-2,-1,-1

; Index is StageObject.timer (0..49).  A stage hit is seeded at 49 because
; update precedes its first render.  Visible timers 48..1 play
; 0,1,2,3,2,1 with exactly eight fields per frame.
monosh_stage_fast_bom_frame_by_timer:
    defb 0,1,1,1,1,1,1,1,1,2,2,2,2,2,2,2
    defb 2,3,3,3,3,3,3,3,3,2,2,2,2,2,2,2
    defb 2,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0
    defb 0,0

SECTION bss_compiler
monosh_stage_fast_attribute_count: defs 1
monosh_stage_fast_camera_step: defs 1
monosh_stage_fast_asset:       defs 1
monosh_stage_fast_type:        defs 1
monosh_stage_fast_z:           defs 1
monosh_stage_fast_lift_level:  defs 1
monosh_stage_fast_lift_odd:    defs 1
monosh_stage_fast_width:       defs 1
monosh_stage_fast_height:      defs 1
monosh_stage_fast_half_width:  defs 1
monosh_stage_fast_center:      defs 2
monosh_stage_fast_bottom:      defs 2
monosh_stage_fast_collision_hitbox: defs 1
monosh_stage_fast_collision_radius: defs 1
monosh_stage_fast_contact_kind: defs 1
monosh_stage_fast_pattern_small: defs 1
monosh_stage_fast_pattern_left: defs 1
monosh_stage_fast_pattern_right: defs 1
monosh_stage_fast_plane_page: defs 1
