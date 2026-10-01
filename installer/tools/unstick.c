/*
 * Keep TopSolid's dialogs from hanging under Wine.
 *
 * TopSolid's ComboBox.WndProc swallows WM_PAINT without validating while its dialog is not loaded
 * yet. Under Wine such a combo box can get invalidated while its dialog is loading (the PDM
 * "Connection" dialog of the first login, command dialogs like Trim or Clean). The dialog's loading
 * pumps messages until the queue is empty (Application.DoEventsAndLockUI), which never happens with
 * an endless WM_PAINT, so the dialog never finishes loading and TopSolid hangs.
 *
 * This watchdog runs next to TopSolid. When a combo box keeps an update region for a few seconds
 * while its thread still answers messages (so TopSolid is pumping, not computing), it validates
 * the pending windows of that thread. That ends the loop; the next repaint draws them normally.
 *
 * It also restarts the Sentinel license server when it stops while TopSolid runs (it crashed once
 * under Wine); without it TopSolid loses its licenses and hangs in the license dialog.
 *
 * Build: x86_64-w64-mingw32-gcc -O2 -o unstick.exe unstick.c
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

#define POLL_MS     1000
#define STUCK_POLLS 5
#define MAX_SEEN    256
#define SERVICE_POLLS 10
#define LICENSE_SERVICE L"Sentinel RMS License Manager"

struct seen { HWND hwnd; int polls; };
static struct seen seen[MAX_SEEN], now[MAX_SEEN];
static int nseen, nnow;
static HWND stuck;
static int validated;

static BOOL needs_paint(HWND hwnd)
{
    RECT r;
    return IsWindowVisible(hwnd) && GetUpdateRect(hwnd, &r, FALSE);
}

static void validate(HWND hwnd)
{
    if (!needs_paint(hwnd)) return;
    RedrawWindow(hwnd, NULL, NULL, RDW_VALIDATE | RDW_NOERASE | RDW_NOFRAME);
    validated++;
}

static BOOL CALLBACK validate_child(HWND hwnd, LPARAM lp) { validate(hwnd); return TRUE; }

static BOOL CALLBACK validate_top(HWND hwnd, LPARAM lp)
{
    validate(hwnd);
    EnumChildWindows(hwnd, validate_child, 0);
    return TRUE;
}

/* count the polls a combo box has been waiting for its WM_PAINT */
static BOOL CALLBACK check_child(HWND hwnd, LPARAM lp)
{
    char cls[128];
    int i, polls = 1;

    GetClassNameA(hwnd, cls, sizeof(cls));
    if (strncmp(cls, "WindowsForms10.COMBOBOX", 23) || !needs_paint(hwnd) || nnow == MAX_SEEN) return TRUE;
    for (i = 0; i < nseen; i++)
        if (seen[i].hwnd == hwnd) polls = seen[i].polls + 1;
    now[nnow].hwnd = hwnd;
    now[nnow++].polls = polls;
    if (polls >= STUCK_POLLS) stuck = hwnd;
    return TRUE;
}

static BOOL CALLBACK check_top(HWND hwnd, LPARAM lp)
{
    EnumChildWindows(hwnd, check_child, 0);
    return TRUE;
}

/* restart the license server if it stopped, unless it was set not to start automatically */
static void keep_license_server(void)
{
    union { QUERY_SERVICE_CONFIGW cfg; BYTE buf[8192]; } u;
    SC_HANDLE scm, svc;
    SERVICE_STATUS st;
    DWORD need;

    if (!(scm = OpenSCManagerW(NULL, NULL, SC_MANAGER_CONNECT))) return;
    if ((svc = OpenServiceW(scm, LICENSE_SERVICE, SERVICE_QUERY_STATUS | SERVICE_QUERY_CONFIG | SERVICE_START)))
    {
        if (QueryServiceStatus(svc, &st) && st.dwCurrentState == SERVICE_STOPPED &&
            QueryServiceConfigW(svc, &u.cfg, sizeof(u), &need) && u.cfg.dwStartType == SERVICE_AUTO_START)
        {
            printf("unstick: the license server had stopped, restarting it: %s\n",
                   StartServiceW(svc, 0, NULL) ? "ok" : "failed");
            fflush(stdout);
        }
        CloseServiceHandle(svc);
    }
    CloseServiceHandle(scm);
}

int main(void)
{
    DWORD_PTR res;
    DWORD tid;
    unsigned int polls = 0;

    for (;;)
    {
        Sleep(POLL_MS);
        if (++polls % SERVICE_POLLS == 0) keep_license_server();
        nnow = 0;
        stuck = NULL;
        EnumWindows(check_top, 0);
        memcpy(seen, now, nnow * sizeof(*now));
        nseen = nnow;
        if (!stuck) continue;

        /* a thread that doesn't answer is busy computing; its windows are painted when it's done */
        if (!SendMessageTimeoutW(GetAncestor(stuck, GA_ROOT), WM_NULL, 0, 0, SMTO_ABORTIFHUNG, 500, &res))
            continue;
        tid = GetWindowThreadProcessId(stuck, NULL);
        validated = 0;
        EnumThreadWindows(tid, validate_top, 0);
        printf("unstick: combo box %p kept waiting for WM_PAINT, validated %d windows\n", stuck, validated);
        fflush(stdout);
        nseen = 0;
    }
}
