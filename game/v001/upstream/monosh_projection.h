#ifndef MSXSH_MONOSH_PROJECTION_H
#define MSXSH_MONOSH_PROJECTION_H

extern unsigned char monosh_projection_scale[];
extern const unsigned char *monosh_ground_depth_pointer;
signed int monosh_project_x(signed int world_x, unsigned char z);

#endif
