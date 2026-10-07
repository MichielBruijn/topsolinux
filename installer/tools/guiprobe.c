/*
 * Print the window state of a program's GUI thread, for the debug command: which window has the
 * keyboard focus, the mouse capture, a menu or a move, and which windows are disabled. Typing that
 * goes nowhere while clicks still work shows up here as a focus on the wrong window.
 *
 * usage: guiprobe PID (hexadecimal, as winedbg shows it)
 */
#include <windows.h>
#include <stdio.h>

static DWORD pid, tid;

static void show(const char *tag, HWND h)
{
    char cls[128] = "", txt[128] = "";
    RECT r = {0};
    DWORD p = 0, t;

    if (!h) { printf("%-10s (none)\n", tag); return; }
    GetClassNameA(h, cls, sizeof cls);
    GetWindowTextA(h, txt, sizeof txt);
    GetWindowRect(h, &r);
    t = GetWindowThreadProcessId(h, &p);
    printf("%-10s %p %s \"%s\" visible=%d enabled=%d style=%08lx exstyle=%08lx rect=%ld,%ld-%ld,%ld parent=%p owner=%p%s\n",
           tag, h, cls, txt, IsWindowVisible(h), IsWindowEnabled(h), GetWindowLongA(h, GWL_STYLE),
           GetWindowLongA(h, GWL_EXSTYLE), r.left, r.top, r.right, r.bottom, GetParent(h), GetWindow(h, GW_OWNER),
           p != pid ? " (other program)" : t != tid ? " (other thread)" : "");
}

static BOOL CALLBACK top(HWND h, LPARAM l)
{
    DWORD p;
    DWORD t = GetWindowThreadProcessId(h, &p);

    if (p != pid || !IsWindowVisible(h)) return TRUE;
    if (!tid) tid = t;
    show("window", h);
    return TRUE;
}

int main(int argc, char **argv)
{
    GUITHREADINFO gi = { sizeof gi };

    if (argc != 2) { fprintf(stderr, "usage: guiprobe PID\n"); return 1; }
    pid = strtoul(argv[1], NULL, 16);
    EnumWindows(top, 0);
    if (!tid) { printf("no visible windows\n"); return 1; }
    if (!GetGUIThreadInfo(tid, &gi)) { printf("GetGUIThreadInfo failed: %lu\n", GetLastError()); return 1; }
    printf("thread %04lx flags %08lx%s%s%s\n", tid, gi.flags, gi.flags & GUI_INMENUMODE ? " in-menu" : "",
           gi.flags & GUI_INMOVESIZE ? " in-move-size" : "", gi.flags & GUI_POPUPMENUMODE ? " popup-menu" : "");
    show("active", gi.hwndActive);
    show("focus", gi.hwndFocus);
    show("capture", gi.hwndCapture);
    show("menu", gi.hwndMenuOwner);
    show("movesize", gi.hwndMoveSize);
    show("caret", gi.hwndCaret);
    show("foreground", GetForegroundWindow());
    return 0;
}
