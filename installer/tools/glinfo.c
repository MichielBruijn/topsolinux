/*
 * Print which OpenGL driver draws TopSolid's 3D view under Wine, for a problem report: slow drawing
 * on llvmpipe means no GPU driver works, and Intel or NVIDIA tells which GPU draws.
 *
 * Build: x86_64-w64-mingw32-gcc -O2 -s -o glinfo.exe glinfo.c -lopengl32 -lgdi32
 */
#include <windows.h>
#include <GL/gl.h>
#include <stdio.h>

int main(void)
{
    PIXELFORMATDESCRIPTOR pfd = { sizeof(pfd), 1, PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER,
                                  PFD_TYPE_RGBA, 32 };
    HWND hwnd = CreateWindowA("static", "glinfo", WS_POPUP, 0, 0, 64, 64, 0, 0, 0, 0);
    HDC dc = GetDC(hwnd);
    HGLRC rc;

    pfd.cDepthBits = 24;
    if (!SetPixelFormat(dc, ChoosePixelFormat(dc, &pfd), &pfd) || !(rc = wglCreateContext(dc)) ||
        !wglMakeCurrent(dc, rc))
    {
        printf("no OpenGL context (error %lu)\n", GetLastError());
        return 1;
    }
    printf("vendor:   %s\nrenderer: %s\nversion:  %s\n", (const char *)glGetString(GL_VENDOR),
           (const char *)glGetString(GL_RENDERER), (const char *)glGetString(GL_VERSION));
    wglMakeCurrent(0, 0);
    wglDeleteContext(rc);
    return 0;
}
