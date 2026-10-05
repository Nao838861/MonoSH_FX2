#include "mode3_sprite.h"
#include "monosh_assets.h"
#include "monosh_combat.h"
#include "monosh_draw.h"
#include "monosh_enemy.h"
#include "monosh_enemy_data.h"
#include "monosh_player.h"
#include "monosh_runtime.h"

#ifdef __ROM__
#pragma bank 2
#endif

#define ENEMY_MAX       8u
#define ENEMY_BULLET_MAX 6u
#define ENEMY_TYPE_EM0  5u
#define ENEMY_TYPE_EM1  6u
#define ENEMY_TYPE_BOM0 2u
#define SPAWN_WAIT_ONLY 0xfeu
#define SPAWN_END       0xffu

typedef struct MonoshEnemy {
    unsigned char active;
    unsigned char type;
    unsigned char pattern;
    unsigned char frame;
    unsigned char x;
    unsigned char bottom;
    unsigned char z;
    unsigned char display;
    unsigned char width;
    unsigned char height;
} MonoshEnemy;

typedef struct MonoshEnemyBullet {
    unsigned char active;
    unsigned char x;
    unsigned char y;
    unsigned char z;
    signed char vx;
    signed char vy;
    unsigned char variant;
} MonoshEnemyBullet;

MonoshEnemy monosh_enemies[ENEMY_MAX];
MonoshEnemyBullet monosh_enemy_bullets[ENEMY_BULLET_MAX];
#define enemies monosh_enemies
#define enemy_bullets monosh_enemy_bullets
unsigned char monosh_enemy_bullet_count;
unsigned char monosh_enemy_spawn_index;
unsigned int monosh_enemy_spawn_wait;
#define spawn_index monosh_enemy_spawn_index
#define spawn_wait  monosh_enemy_spawn_wait
unsigned int monosh_enemy_em1_phase[ENEMY_MAX];
#define em1_phase monosh_enemy_em1_phase
/* ROM EM1 keeps the source state/subtimer in em1_phase and uses this byte
   for the source shrink accumulator.  Keeping it separate avoids turning
   the hot ten-byte enemy record into a larger stride. */
unsigned char monosh_enemy_em1_shrink[ENEMY_MAX];
signed char monosh_enemy_camera_delta_cached;
#define enemy_camera_delta_cached monosh_enemy_camera_delta_cached
unsigned char monosh_enemy_active_count_value;
#define active_count monosh_enemy_active_count_value
unsigned char monosh_enemy_em1_count;
unsigned char monosh_enemy_stage_complete_flag;
#define stage_complete monosh_enemy_stage_complete_flag
/* DOS cannot afford the extra 3.2 KiB of patterns; its renderer falls back
   to the single open pose while ROM sets this after the page-2 upload. */
unsigned char monosh_em1_animation_assets_ready;
/* Debugger ABI: tests and external tools may still invalidate this legacy
   byte even though the 60 Hz ROM renderer no longer consumes a body cache. */
unsigned char monosh_enemy_draw_cache_valid;
/* Debugger ABI only: the 60 Hz renderer no longer branches on this value. */
unsigned char monosh_enemy_half_frame;
unsigned char monosh_enemy_collision_cursor;
unsigned char monosh_enemy_player_hit;
#define player_hit monosh_enemy_player_hit
#define current_player_x monosh_player_x
#define current_player_bottom monosh_player_bottom
extern signed char monosh_ground_screen_delta;

void monosh_enemy_fast_render(void);
void monosh_enemy_fast_update_bullets(void);
void monosh_enemy_fast_advance(void);
void monosh_enemy_fast_check_player_bullets(void);
void monosh_enemy_fast_render_bullets(void);
void monosh_enemy_fast_update_em1(void);
unsigned char monosh_enemy_fast_spawn_due(void);
void monosh_enemy_fast_add(unsigned int packed) __z88dk_fastcall;
extern unsigned char mode3_attribute_count;

static void rebuild_buckets(void)
{
    /* Draw order is compiled explicitly; R25.SPS rotation remains disabled. */
}

static unsigned char velocity_for(unsigned char z, unsigned char distance)
{
    unsigned int index = (unsigned int)((z >> 1) - 4u) << 6;
    index += distance;
    return monosh_ebullet_velocity[index];
}

static unsigned char fire_enemy_bullet_variant(unsigned char source_x,
                                                unsigned char source_bottom,
                                                unsigned char z,
                                                unsigned char variant)
{
    unsigned char player_vbuf_x;
    MonoshEnemyBullet *bullet;
    unsigned char distance;
    unsigned char velocity;

    if (monosh_enemy_bullet_count == ENEMY_BULLET_MAX || z < 8u) return 0u;
    /* current_player_x is the absolute MSX screen centre (source X + 128).
       MonoSH deliberately aims/collides at 124 + sourceX/2, so the matching
       conversion is screenX/2 + 60, not the geometric-centre bias +64. */
    player_vbuf_x = (unsigned char)((current_player_x >> 1) + 60);
    /* Projectile slots are dense, just like enemy bodies.  Allocation is an
       append and removal swaps the former last slot into the hole. */
    bullet = &enemy_bullets[monosh_enemy_bullet_count];
    bullet->x = source_x;
    bullet->y = source_bottom;
    bullet->z = z;

    if (player_vbuf_x >= bullet->x) {
        distance = (unsigned char)(player_vbuf_x - bullet->x) >> 2;
        if (distance > 63u) distance = 63u;
        bullet->vx = (signed char)((velocity_for(z, distance) + 1u) >> 1);
    } else {
        distance = (unsigned char)(bullet->x - player_vbuf_x) >> 2;
        if (distance > 63u) distance = 63u;
        bullet->vx = -(signed char)((velocity_for(z, distance) + 1u) >> 1);
    }

    if ((unsigned int)current_player_bottom >= bullet->y) {
        distance = (unsigned char)(current_player_bottom - bullet->y) >> 2;
        if (distance > 63u) distance = 63u;
        velocity = velocity_for(z, distance);
        bullet->vy = (signed char)((velocity + 1u) >> 1);
    } else {
        distance = (unsigned char)(bullet->y - current_player_bottom) >> 2;
        if (distance > 63u) distance = 63u;
        velocity = velocity_for(z, distance);
        bullet->vy = -(signed char)((velocity + 1u) >> 1);
    }
    if (variant < 3u) {
        /* Normal shots start the 64-field rotation at master frame 0. */
        bullet->variant = 0u;
    } else {
        /* Bit 7 keeps the boss projectile on its independent artwork. */
        bullet->variant = 0x80u;
    }
    bullet->active = 1u;
    ++monosh_enemy_bullet_count;
    return 1u;
}

static void fire_enemy_bullet_at(unsigned char source_x,
                                 unsigned char source_bottom,
                                 unsigned char z)
{
    (void)fire_enemy_bullet_variant(source_x, source_bottom, z, 0u);
}

void monosh_enemy_fire_at(unsigned char virtual_x,
                          unsigned char bottom,
                          unsigned char z)
{
    fire_enemy_bullet_at(virtual_x, bottom, z);
}

unsigned char monosh_enemy_fire_boss_at(unsigned char virtual_x,
                                        unsigned char bottom,
                                        unsigned char z)
{
    return fire_enemy_bullet_variant(virtual_x, bottom, z, 3u);
}

static void update_em0_geometry(MonoshEnemy *enemy,
                                const MonoshEnemyPath *path)
{
    const unsigned char *sample = path->samples +
                                  (unsigned int)enemy->frame * 3u;
    unsigned char geometry_z;
    enemy->x = sample[0];
    enemy->bottom = sample[1];
    enemy->z = sample[2];
    /* Some source paths enter at wz=224, which becomes logical Z=112 after
       the 60 Hz conversion.  Keep that path depth, but clamp the picture
       lookup exactly like the assembly update path does. */
    geometry_z = enemy->z > 110u ? 110u : enemy->z;
    {
        const unsigned char *geometry =
            monosh_enemy_geometry + (unsigned int)geometry_z * 2u;
        enemy->width = geometry[0];
        enemy->height = geometry[1];
    }
    if ((unsigned char)(enemy->frame + 1u) < path->frames) {
        enemy->display = (unsigned char)(sample[0] > sample[3]);
    } else {
        enemy->display = 0u;
    }
}

static void fire_enemy_bullet(const MonoshEnemy *enemy)
{
    fire_enemy_bullet_at(enemy->x, enemy->bottom,
                         enemy->z);
}

/* Called directly by the bank-resident fast advance loop while bank 2 is
   mapped.  HL carries the current enemy slot and firing deliberately occurs
   before its path frame is advanced. */
#ifndef __ROM__
void monosh_enemy_fire_em0_fast(const MonoshEnemy *enemy) __z88dk_fastcall
{
    fire_enemy_bullet(enemy);
}
#endif

static unsigned char em1_screen_bottom(const MonoshEnemy *enemy)
{
    signed int bottom;
    /* Rendering uses the formation Y directly as the lower anchor, lifting
       EM1 by half its scaled height.  Spawn its projectile at that same
       screen-space anchor so it remains attached to the visible character. */
    bottom = (signed int)enemy->bottom + monosh_ground_screen_delta;
    if (bottom < 0) bottom = 0;
    if (bottom > 223) bottom = 223;
    return (unsigned char)bottom;
}

#ifndef __ROM__
static void update_em1(MonoshEnemy *enemy, unsigned char slot)
{
    unsigned int phase;
    unsigned char lane = (unsigned char)(enemy->pattern & 3u);
    unsigned char target_x = lane == 0u ? 128u : (lane == 1u ? 107u : 149u);
    unsigned char target_bottom = lane == 0u ? 72u : 144u;
    unsigned char local = 0xffu;
    /* Keep the byte frame as a debug/test injection hook.  Runtime-spawned
       EM1 starts at zero; a non-zero source frame is converted once to the
       doubled 60 Hz timeline. */
    if (enemy->frame != 0u) {
        em1_phase[slot] = (unsigned int)enemy->frame * 2u;
        enemy->frame = 0u;
    }
    phase = ++em1_phase[slot];
    if (phase < 12u) {
        if (enemy->x < target_x) {
            enemy->x = (unsigned char)(enemy->x + 2u);
            if (enemy->x > target_x) enemy->x = target_x;
        } else if (enemy->x > target_x) {
            enemy->x = (unsigned char)(enemy->x - 2u);
            if (enemy->x < target_x) enemy->x = target_x;
        }
        if (enemy->bottom < target_bottom) {
            enemy->bottom = (unsigned char)(enemy->bottom + 4u);
            if (enemy->bottom > target_bottom) enemy->bottom = target_bottom;
        } else if (enemy->bottom > target_bottom) {
            enemy->bottom = (unsigned char)(enemy->bottom - 4u);
            if (enemy->bottom < target_bottom) enemy->bottom = target_bottom;
        }
        enemy->display = 0u;
    } else if (phase < 20u) {
        if (enemy->z > 96u) enemy->z = (unsigned char)(enemy->z - 2u);
        enemy->display = 0u;
    } else if (phase < 142u) {
        enemy->z = 96u;
        local = (unsigned char)(phase - 20u);
    } else if (phase < 158u) {
        if (enemy->z > 66u) enemy->z = (unsigned char)(enemy->z - 2u);
        enemy->display = 0u;
    } else if (phase < 280u) {
        enemy->z = 66u;
        local = (unsigned char)(phase - 158u);
    } else if (phase < 294u) {
        if (enemy->z > 40u) enemy->z = (unsigned char)(enemy->z - 2u);
        enemy->display = 0u;
    } else if (phase < 416u) {
        enemy->z = 40u;
        local = (unsigned char)(phase - 294u);
    } else if (phase < 476u) {
        if (enemy->x < 128u) ++enemy->x;
        else if (enemy->x > 128u) --enemy->x;
        if (enemy->bottom < 120u) ++enemy->bottom;
        else if (enemy->bottom > 120u) --enemy->bottom;
        if (enemy->z < 110u) ++enemy->z;
        enemy->display = 0u;
    } else {
        enemy->x = 128u;
        enemy->bottom = 120u;
        enemy->display = 0u;
        if (enemy->z < 110u) ++enemy->z;
        if (enemy->z >= 110u || phase >= 510u) {
            unsigned char last;
            --active_count;
            --monosh_enemy_em1_count;
            last = active_count;
            if (slot != last) {
                *enemy = enemies[last];
                em1_phase[slot] = em1_phase[last];
            }
            enemies[last].active = 0u;
            em1_phase[last] = 0u;
        }
    }
    if (local != 0xffu) {
        unsigned char fire_time = lane == 0u ? 60u : (lane == 2u ? 66u : 72u);
        if (local < 30u) {
            enemy->display = (unsigned char)(local / 6u + 1u);
        } else if (local < 90u) {
            enemy->display = 0x85u; /* vulnerable, fully open */
        } else if (local < 120u) {
            enemy->display = (unsigned char)(5u - (local - 90u) / 6u);
        } else {
            enemy->display = 0u;
        }
        if (local == fire_time) {
            fire_enemy_bullet_at(enemy->x, em1_screen_bottom(enemy), enemy->z);
        }
    }
}
#else
/* Rare side effects for the bank-resident EM1 state machine.  Keeping these
   as fastcall helpers avoids pulling the C 16-bit phase dispatcher back into
   every field. */
void monosh_enemy_fire_em1_fast(const MonoshEnemy *enemy) __z88dk_fastcall
{
    fire_enemy_bullet_at(enemy->x, em1_screen_bottom(enemy), enemy->z);
}

void monosh_enemy_remove_em1_fast(unsigned char slot) __z88dk_fastcall
{
    unsigned char last;
    --active_count;
    --monosh_enemy_em1_count;
    last = active_count;
    if (slot != last) {
        enemies[slot] = enemies[last];
        em1_phase[slot] = em1_phase[last];
        monosh_enemy_em1_shrink[slot] = monosh_enemy_em1_shrink[last];
    }
    enemies[last].active = 0u;
    em1_phase[last] = 0u;
    monosh_enemy_em1_shrink[last] = 0u;
}
#endif

static void add_enemy(unsigned char type, unsigned char pattern)
{
    unsigned char i;

    if (active_count == ENEMY_MAX ||
        (type != ENEMY_TYPE_EM0 && type != ENEMY_TYPE_EM1)) return;
    /* Active enemies are kept dense in slots 0..active_count-1.  Both the
       update and render assembly can therefore stop at the live count
       instead of testing sixteen empty slots per field. */
    i = active_count;
    enemies[i].active = 1u;
    enemies[i].type = type;
    enemies[i].pattern = pattern;
    enemies[i].frame = 0u;
    enemies[i].x = 128u;
    enemies[i].bottom = 120u;
    enemies[i].z = type == ENEMY_TYPE_EM1 ? 110u : 96u;
    em1_phase[i] = 0u;
    monosh_enemy_em1_shrink[i] = 0u;
    enemies[i].display = 0u;
    if (type == ENEMY_TYPE_EM0) {
        update_em0_geometry(&enemies[i], &monosh_enemy_paths[pattern]);
    } else {
        ++monosh_enemy_em1_count;
    }
    ++active_count;
}

static void logic_tick(void)
{
    unsigned char i;
    unsigned char guard;

    /* During the boss encounter the completed Stage 1 enemy list is empty.
       Keep projectile motion, but skip three redundant eight-slot scans. */
    if (stage_complete && active_count == 0u) {
        if (monosh_enemy_bullet_count != 0u) {
            monosh_enemy_fast_update_bullets();
        }
        return;
    }

    if (monosh_enemy_em1_count != 0u) {
#ifdef __ROM__
        monosh_enemy_fast_update_em1();
#else
        i = 0u;
        while (i != active_count) {
            MonoshEnemy *enemy = &enemies[i];
            if (enemy->active && enemy->type == ENEMY_TYPE_EM1) {
                unsigned char before = active_count;
                update_em1(enemy, i);
                if (active_count != before) continue;
            }
            ++i;
        }
#endif
    }
    monosh_enemy_fast_advance();
    if (monosh_enemy_bullet_count != 0u) monosh_enemy_fast_update_bullets();
    /* MonoSH checks every live shot against the complete shared object list
       on each 30 Hz game update.  The common Z mask rejects distant targets
       before X/Y and one projected rectangle serves all three shots. */
    if (monosh_player_bullet_count != 0u && active_count != 0u &&
        (monosh_runtime_frame_counter & 1u) == 0u) {
        monosh_enemy_fast_check_player_bullets();
    }

    if (stage_complete) return;
    /* The NES table is only dereferenced when its relative timer expires.
       Keep the 16-bit interpolated wait as a bank-local countdown as well;
       the common field is now one small assembly decrement instead of a
       structure address calculation plus two 16-bit C comparisons. */
    if (!monosh_enemy_fast_spawn_due()) return;
    for (guard = 0u; guard != 32u; ++guard) {
        const MonoshEnemySpawn *entry = &monosh_enemy_spawns[spawn_index];

        if (entry->type == SPAWN_END) {
            spawn_wait = 0u;
            stage_complete = 1u;
            return;
        }
        if (entry->type != SPAWN_WAIT_ONLY) {
#ifdef __ROM__
            monosh_enemy_fast_add(
                ((unsigned int)entry->type << 8) | entry->pattern);
#else
            add_enemy(entry->type, entry->pattern);
#endif
        }
        ++spawn_index;
        spawn_wait = monosh_enemy_spawns[spawn_index].wait;
        /* Account for this update as the first elapsed field, exactly like
           the source incrementing wait from zero before returning. */
        if (!monosh_enemy_fast_spawn_due()) return;
    }
}

void monosh_enemy_init(void)
{
    unsigned char i;

    for (i = 0u; i != ENEMY_MAX; ++i) {
        enemies[i].active = 0u;
        em1_phase[i] = 0u;
        monosh_enemy_em1_shrink[i] = 0u;
    }
    for (i = 0u; i != ENEMY_BULLET_MAX; ++i) enemy_bullets[i].active = 0u;
    spawn_index = 0u;
    spawn_wait = monosh_enemy_spawns[0].wait;
    active_count = 0u;
    monosh_enemy_em1_count = 0u;
    /* All state transitions now run at 60 Hz; generated paths/waits contain
       the inserted mid-fields and retain the original real-time duration. */
    stage_complete = 0u;
    monosh_enemy_bullet_count = 0u;
    player_hit = 0u;
    monosh_enemy_collision_cursor = 0u;
    enemy_camera_delta_cached = monosh_ground_screen_delta;
    rebuild_buckets();
}

static void enemy_update(void)
{
    logic_tick();
}

static void enemy_render(void)
{
    if (monosh_enemy_bullet_count != 0u) {
        monosh_enemy_fast_render_bullets();
    }
    if (active_count != 0u) {
        /* Every body changes position or scale on each interpolated field.
           The former cache condition was therefore always true and only
           added C-side branches and state stores before direct emission. */
        monosh_enemy_fast_render();
    }
}

#ifndef __ROM__
unsigned char monosh_enemy_frame(void)
{
    unsigned char hit;

    enemy_update();
    /* EM0 geometry was rebuilt against this field's camera offset.  Keep the
       frozen-world delta anchored to the same projection. */
    enemy_camera_delta_cached = monosh_ground_screen_delta;
    enemy_render();
    hit = player_hit;
    player_hit = 0u;
    return hit;
}
#endif

void monosh_enemy_render_only(void)
{
    signed char camera_shift = (signed char)(
        monosh_ground_screen_delta - enemy_camera_delta_cached);
    if (camera_shift != 0) {
        unsigned char i;
        /* NES draw_ground_bgfar_frozen adjusts cached EM0 screen bottoms
           without advancing paths, AI, fire, collision or depth.  Enemy
           explosions share the same cached screen-space anchor here and
           need the same camera-only translation.  EM1 is excluded because
           its renderer applies the absolute camera delta every field. */
        for (i = 0u; i != active_count; ++i) {
            if (enemies[i].type == ENEMY_TYPE_EM0 ||
                enemies[i].type == ENEMY_TYPE_BOM0) {
                enemies[i].bottom = (unsigned char)(
                    (signed int)enemies[i].bottom + camera_shift);
            }
        }
        enemy_camera_delta_cached = monosh_ground_screen_delta;
    }
    enemy_render();
}

unsigned char monosh_enemy_active_count(void)
{
    return active_count;
}

unsigned char monosh_enemy_stage_complete(void)
{
    return stage_complete;
}
