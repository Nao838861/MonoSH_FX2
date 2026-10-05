#include "monosh_projection.h"

#ifdef __ROM__
#pragma bank 3
#endif
const unsigned char monosh_projection_c_anchor = 0u;

#ifndef __ROM__
static const unsigned int monosh_projection_full_scale[111] = {
    408,390,371,360,348,340,331,313,294,290,286,273,260,255,249,243,236,229,222,216,209,202,195,189,183,178,172,168,164,160,156,152,148,145,142,138,134,131,128,124,120,117,114,111,108,105,102,99,96,94,92,89,86,84,82,80,78,76,74,72,70,68,66,64,62,60,58,57,56,54,52,51,50,49,48,46,44,43,42,41,40,40,40,39,38,37,36,36,36,35,34,34,34,33,32,32,32,32,32,31,30,30,30,30,30,30,30,30,30,30,30
};

signed int monosh_project_x(signed int world_x, unsigned char z)
{
    unsigned int distance;
    unsigned int magnitude;
    unsigned char negative = 0u;

    if (world_x < 0) {
        negative = 1u;
        distance = (unsigned int)(-world_x);
    } else {
        distance = (unsigned int)world_x;
    }
    if (z > 110u) z = 110u;
    {
        unsigned long scaled = (unsigned long)distance *
            monosh_projection_full_scale[z];
        magnitude = (unsigned int)(scaled >> 8);
        if (magnitude > 384u) magnitude = 384u;
    }
    return negative ? -(signed int)magnitude : (signed int)magnitude;
}
#endif
