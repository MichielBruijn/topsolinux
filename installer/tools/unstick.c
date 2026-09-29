/*
 * Work around the hanging first PDM login of TopSolid under Wine.
 *
 * The combo boxes of TopSolid's "Connection" dialog get invalidated while the dialog is not yet
 * loaded, and TopSolid's ComboBox.WndProc swallows WM_PAINT without validating them. The resulting
 * endless WM_PAINT keeps Application.Idle from ever running, so the dialog never finishes loading.
 * Validating those combo boxes from outside breaks the loop; the next repaint draws them normally.
 *
 * Build: x86_64-w64-mingw32-gcc -O2 -o unstick.exe unstick.c
 */
#include <windows.h>
#include <string.h>

static BOOL CALLBACK child_proc(HWND hwnd, LPARAM lp)
{
    char cls[128];
    RECT r;

    GetClassNameA(hwnd, cls, sizeof(cls));
    if (strstr(cls, "COMBOBOX") && GetUpdateRect(hwnd, &r, FALSE))
        RedrawWindow(hwnd, NULL, NULL, RDW_VALIDATE | RDW_NOERASE | RDW_NOFRAME);
    return TRUE;
}

static BOOL CALLBACK top_proc(HWND hwnd, LPARAM lp)
{
    char title[128];

    GetWindowTextA(hwnd, title, sizeof(title));
    if (!strcmp(title, "Connection")) EnumChildWindows(hwnd, child_proc, 0);
    return TRUE;
}

int main(void)
{
    EnumWindows(top_proc, 0);
    return 0;
}
