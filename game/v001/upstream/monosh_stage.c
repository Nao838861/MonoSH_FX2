#include "monosh_draw.h"
#include "monosh_combat.h"
#include "monosh_projection.h"
#include "monosh_player.h"
#include "monosh_runtime.h"
#include "monosh_stage.h"
#include "monosh_stage_data.h"

#ifdef __ROM__
#pragma bank 3
#endif

#define STAGE_OBJECT_MAX 16u
#define STAGE_START_FRAME 256u
#define OBJECT_TREE0      1u
#define OBJECT_BOM0       2u
#define OBJECT_BUSH0      3u
#define OBJECT_FLYSTONE   4u
#define OBJECT_EM0        5u
#define OBJECT_BUSH1      7u
#define OBJECT_END        255u
/* Source collision radii use half-resolution VBUF coordinates.  Use the dense
   opaque core of each enlarged V9968 sprite rather than its sparse outline.
   Bush art has especially long side leaves, while FlyStone tapers sharply at
   both ends and therefore needs a narrower core than its full 80-pixel art. */
#define TREE0_PLAYER_CONTACT_RADIUS     36
#define FLYSTONE_PLAYER_CONTACT_RADIUS  32
#define BUSH0_PLAYER_CONTACT_RADIUS     54
#define BUSH1_PLAYER_CONTACT_RADIUS     74
#define PLAYER_GROUND_BOTTOM           201
#define BUSH_CONTACT_MIN_BOTTOM         196

typedef struct StageObject {
    signed int world_x;
    unsigned char depth2;
    unsigned char type;
    unsigned char data;  /* explosion fall level, 0..12 */
    unsigned char timer; /* 60 Hz explosion lifetime */
} StageObject;

/* Filled by the ROM renderer after projection.  Collision consumes exactly
   the same on-screen geometry instead of projecting every bullet again. */
typedef struct StageHitbox {
    StageObject *object;
    unsigned char z;
    unsigned char width;
    unsigned char height;
    signed int center_x;
    unsigned char bottom_y;
} StageHitbox;

StageObject monosh_stage_objects[STAGE_OBJECT_MAX];
unsigned char monosh_stage_object_count;
unsigned char monosh_stage_spawn_index;
unsigned int monosh_stage_frame_counter;
unsigned int monosh_stage_spawn_wait;
unsigned char monosh_stage_half_frame;
unsigned char monosh_stage_near_count;
StageHitbox monosh_stage_hitboxes[STAGE_OBJECT_MAX];
unsigned char monosh_stage_hitbox_count;
unsigned char monosh_stage_need_hitboxes;
unsigned char monosh_stage_contact_result;
/* Retain the public debugger byte; the removed 30 Hz cache itself is gone. */
unsigned char monosh_stage_draw_cache_valid;
unsigned char monosh_stage_collision_bullet_cursor;
unsigned char monosh_stage_collision_bullet_index;
extern signed char monosh_ground_screen_delta;
extern const unsigned char *monosh_ground_depth_pointer;

void monosh_stage_fast_update_positions(signed char camera_step)
    __z88dk_fastcall;
void monosh_stage_fast_render(void);
void monosh_stage_fast_update(signed int player_screen_x)
    __z88dk_fastcall;
void monosh_stage_fast_check_player_bullets(void);
unsigned char monosh_stage_fast_select_collision_bullet(void);
extern unsigned char mode3_attribute_count;

#define objects      monosh_stage_objects
#define object_count monosh_stage_object_count
#define spawn_index  monosh_stage_spawn_index
#define stage_frame  monosh_stage_frame_counter
#define half_frame   monosh_stage_half_frame

static unsigned char asset_index_for_type(unsigned char type)
{
    if (type == OBJECT_BUSH0) return 0u;
    if (type == OBJECT_BUSH1) return 1u;
    if (type == OBJECT_FLYSTONE) return 2u;
    if (type == OBJECT_EM0) return 3u;
    if (type == OBJECT_TREE0) return 4u;
    if (type == OBJECT_BOM0) return 5u;
    return 1u;
}

static void add_object(unsigned char type, signed int world_x,
                       unsigned char data)
{
    StageObject *obj;
    if (object_count == STAGE_OBJECT_MAX) return;
    obj = &objects[object_count++];
    obj->world_x = world_x;
    obj->depth2 = 110u;
    obj->type = type;
    obj->data = data;
    obj->timer = 0u;
}

static void remove_object(unsigned char index)
{
    --object_count;
    if (index != object_count) objects[index] = objects[object_count];
}

void monosh_stage_init(void)
{
    object_count = 0u;
    spawn_index = 0u;
    stage_frame = STAGE_START_FRAME;
    /* The fast ROM path checks zero before decrementing.  Entry 270 becomes
       due on the 14th update after the source-equivalent start at 256. */
    monosh_stage_spawn_wait = 13u;
    half_frame = 0u;
    /* Broad phase remains amortised, but all motion is true 60 Hz. */
    monosh_stage_collision_bullet_cursor = 0u;
    monosh_stage_collision_bullet_index = 0u;
    monosh_stage_hitbox_count = 0u;
}

static void stage_update(signed int player_screen_x)
{
#ifdef __ROM__
    monosh_stage_fast_update(player_screen_x);
#else
    signed char camera_step = (signed char)((player_screen_x - 128) >> 4);
    signed char camera_magnitude;
    unsigned char i = 0u;

    monosh_stage_near_count = 0u;

    half_frame ^= 1u;
    if (camera_step < 0) {
        camera_magnitude = (signed char)-camera_step;
        camera_step = (signed char)-(signed char)(
            (camera_magnitude >> 1) +
            (half_frame != 0u && (camera_magnitude & 1) != 0));
    } else {
        camera_step = (signed char)(
            (camera_step >> 1) +
            (half_frame != 0u && (camera_step & 1) != 0));
    }
    ++stage_frame;
    while (spawn_index < monosh_stage1_spawn_count &&
           monosh_stage1_spawns[spawn_index].frame <= stage_frame) {
        const MonoshSpawnEntry *entry = &monosh_stage1_spawns[spawn_index];
        if (entry->type == OBJECT_END) break;
        add_object(entry->type, entry->world_x, entry->data);
        ++spawn_index;
    }

    while (i < object_count) {
        StageObject *obj = &objects[i];
        if (obj->type == OBJECT_BOM0) {
            if (obj->timer == 0u) {
                remove_object(i);
                continue;
            }
            --obj->timer;
            if (obj->data != 0u) --obj->data;
            if (obj->depth2 < 3u) {
                remove_object(i);
                continue;
            }
        }
        if (obj->depth2 == 0u) {
            remove_object(i);
            continue;
        }
        --obj->depth2;
        if (obj->depth2 == 0u) monosh_stage_near_count = 1u;
        obj->world_x -= camera_step;
        ++i;
    }
#endif
}

static void stage_render(void)
{
#ifdef __ROM__
    monosh_stage_fast_render();
#else
    unsigned char index;

    for (index = 0u; index != object_count; ++index) {
            const StageObject *obj = &objects[index];
            unsigned char asset_index = asset_index_for_type(obj->type);
            unsigned char z = obj->depth2;
            const unsigned char *geometry =
                monosh_stage_geometry[asset_index] + (unsigned int)z * 4u;
            unsigned char width = geometry[0];
            unsigned char height = geometry[1];
            signed int wx = obj->world_x;
            signed int projected = monosh_project_x(wx, z);
            signed int center_x = (signed int)(128 + projected);
            signed int bottom_y = geometry[2];
            signed int half_width = geometry[3];

#ifdef __ROM__
            bottom_y = (signed int)(207u -
                monosh_ground_depth_pointer[219u - (unsigned char)bottom_y]);
#else
            bottom_y += monosh_ground_screen_delta;
#endif
            if (obj->type == OBJECT_TREE0 || obj->type == OBJECT_BUSH0 ||
                obj->type == OBJECT_BUSH1) {
                bottom_y += z >> 5;
            }

            if (obj->type == OBJECT_FLYSTONE) {
                bottom_y -= monosh_stage_lift[6][z];
            } else if (obj->type == OBJECT_BOM0 && obj->data != 0u) {
                unsigned char level = obj->data > 12u ? 12u : obj->data;
                unsigned char table = level >> 1;
                unsigned char lift = monosh_stage_lift[table][z];
                if ((level & 1u) != 0u) {
                    lift = (unsigned char)((lift +
                        monosh_stage_lift[table + 1u][z] + 1u) >> 1);
                }
                bottom_y -= lift;
            }

            if (center_x + half_width >= 0 &&
                center_x - half_width < 256 &&
                bottom_y > 0 && bottom_y - height < 212) {
                if (monosh_draw_count != MONOSH_DRAW_MAX) {
                    MonoshDrawCommand *command =
                        &monosh_draw_commands[monosh_draw_count++];
                    command->center_x = center_x;
                    command->bottom_y = bottom_y;
                    command->width = width;
                    command->height = height;
                    command->flags = 0u;
                    if (obj->type == OBJECT_BUSH0) command->asset = MONOSH_DRAW_BUSH0;
                    else if (obj->type == OBJECT_BUSH1) command->asset = MONOSH_DRAW_BUSH1;
                    else if (obj->type == OBJECT_FLYSTONE) command->asset = MONOSH_DRAW_FLYSTONE;
                    else if (obj->type == OBJECT_TREE0) command->asset = MONOSH_DRAW_TREE0;
                    else command->asset = MONOSH_DRAW_BOM0;
                }
            }
    }
#endif
}

static signed int abs_difference(signed int a, signed int b)
{
    signed int difference = a - b;
    return difference < 0 ? -difference : difference;
}

static void object_geometry(const StageObject *obj,
                            signed int *center_x,
                            signed int *bottom_y,
                            unsigned char *width,
                            unsigned char *height)
{
    unsigned char z = obj->depth2;
    unsigned char asset = asset_index_for_type(obj->type);
    const unsigned char *geometry =
        monosh_stage_geometry[asset] + (unsigned int)z * 4u;
    *width = geometry[0];
    *height = geometry[1];
#ifdef __ROM__
    /* Contact is evaluated only at the source-equivalent Z2=0 field.  The
       one-pixel endpoint difference is inside the collision margin and
       avoids pulling the general C multiply path into the hot ROM bank. */
    *center_x = (signed int)(128 + obj->world_x);
#else
    *center_x = (signed int)(128 + monosh_project_x(obj->world_x, z));
#endif
    *bottom_y = geometry[2];
#ifdef __ROM__
    *bottom_y = (signed int)(207u -
        monosh_ground_depth_pointer[219u - (unsigned char)*bottom_y]);
#else
    *bottom_y += monosh_ground_screen_delta;
#endif
    if (obj->type == OBJECT_TREE0 || obj->type == OBJECT_BUSH0 ||
        obj->type == OBJECT_BUSH1) {
        *bottom_y += z >> 5;
    }
    if (obj->type == OBJECT_FLYSTONE) {
        *bottom_y -= monosh_stage_lift[6][z];
    }
}

static void check_player_bullets(void)
{
#ifdef __ROM__
    monosh_stage_fast_check_player_bullets();
#else
    unsigned char hi;
    if (monosh_player_bullet_count == 0u) return;
    for (hi = 0u; hi != monosh_stage_hitbox_count; ++hi) {
        const StageHitbox *hitbox = &monosh_stage_hitboxes[hi];
        StageObject *obj = hitbox->object;
        unsigned char bi;
        signed int top_y = (signed int)hitbox->bottom_y - hitbox->height;

        if (obj->type == OBJECT_BOM0) continue;
        for (bi = 0u; bi != MONOSH_PLAYER_BULLET_MAX; ++bi) {
            MonoshPlayerBullet *bullet = &monosh_player_bullets[bi];
            unsigned char fall_level;
            signed int dz = (signed int)hitbox->z -
                            (signed int)((unsigned int)bullet->wz << 1);
            if (bullet->active != 1u || dz < -8 || dz > 1) continue;
            if (top_y < 0 || (signed int)bullet->screen_y < top_y ||
                bullet->screen_y > hitbox->bottom_y) continue;
            if (abs_difference(hitbox->center_x, bullet->screen_x) >
                (signed int)(hitbox->width >> 1)) continue;

            bullet->active = 0u;
            --monosh_player_bullet_count;
            fall_level = obj->type == OBJECT_FLYSTONE ? 12u : 0u;
            obj->type = OBJECT_BOM0;
            obj->data = fall_level;
            /* Stage collision runs after rendering.  The next update consumes
               one tick before the explosion can first be displayed. */
            obj->timer = 49u;
            break;
        }
    }
#endif
}

static unsigned char check_player_contact(signed int player_screen_x,
                                          signed int player_bottom)
{
    unsigned char oi;
    if (!monosh_stage_near_count) return 0u;
    for (oi = 0u; oi != object_count; ++oi) {
        const StageObject *obj = &objects[oi];
        unsigned char width;
        unsigned char height;
        signed int center_x;
        signed int bottom_y;
        signed int top_y;
        signed int contact_radius;
        /* Z2=1 is the newly inserted 60 Hz midpoint.  The source collision
           happened only at logical Z=0, so do not add an early hit field. */
        if (obj->depth2 != 0u || obj->type == OBJECT_BOM0) continue;
        if (obj->type != OBJECT_TREE0 && obj->type != OBJECT_BUSH0 &&
            obj->type != OBJECT_FLYSTONE && obj->type != OBJECT_BUSH1) continue;
        /* A Bush remains a ground trip hazard during only the first 4/5-pixel
           lift step.  Six or more pixels above the ground clears it. */
        if ((obj->type == OBJECT_BUSH0 || obj->type == OBJECT_BUSH1) &&
            player_bottom < BUSH_CONTACT_MIN_BOTTOM) continue;
        object_geometry(obj, &center_x, &bottom_y, &width, &height);
        if (obj->type == OBJECT_TREE0) {
            contact_radius = TREE0_PLAYER_CONTACT_RADIUS;
        } else if (obj->type == OBJECT_FLYSTONE) {
            contact_radius = FLYSTONE_PLAYER_CONTACT_RADIUS;
        } else if (obj->type == OBJECT_BUSH0) {
            contact_radius = BUSH0_PLAYER_CONTACT_RADIUS;
        } else {
            contact_radius = BUSH1_PLAYER_CONTACT_RADIUS;
        }
        if (abs_difference(center_x, player_screen_x) > contact_radius) continue;
        top_y = bottom_y - height;
        if (bottom_y < player_bottom - 40 || top_y > player_bottom + 8) continue;
        if (obj->type == OBJECT_BUSH0 || obj->type == OBJECT_BUSH1) return 2u;
        return 1u;
    }
    return 0u;
}

#ifndef __ROM__
unsigned char monosh_stage_frame(void)
{
    unsigned char contact;
    stage_update(monosh_player_x);
#ifdef __ROM__
    /* Enemy and Stage collision own opposite 60 Hz fields.  Every target
       keeps a 30 Hz cadence while neither field pays both complete lists. */
    monosh_stage_need_hitboxes = (unsigned char)(
        monosh_player_bullet_count != 0u &&
        (monosh_runtime_frame_counter & 1u) != 0u);
#endif
    /* The ROM renderer resolves all live shots while each projected
       rectangle is still live, avoiding a second hitbox-array walk. */
    stage_render();
#ifdef __ROM__
    contact = monosh_stage_contact_result;
#else
    contact = monosh_stage_near_count ?
        check_player_contact(monosh_player_x, monosh_player_bottom) : 0u;
#endif
    return contact;
}
#endif


void monosh_stage_render_only(void)
{
    stage_render();
}

unsigned char monosh_stage_is_clear(void)
{
    return (unsigned char)(object_count == 0u);
}
