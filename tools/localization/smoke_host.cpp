// Disposable game-like process: loads a real DLL and reports hooked GDI results.
#include <windows.h>
#include <cstdio>
#include <cstdlib>
#include <cwchar>

static LRESULT CALLBACK HostProc(HWND window, UINT message, WPARAM wp, LPARAM lp) {
    if (message == WM_TIMER) {
        HFONT font = CreateFontW(-20, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
            DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Arial");
        HDC dc = GetDC(window);
        HGDIOBJ old = SelectObject(dc, font);
        wchar_t face[128] = {};
        GetTextFaceW(dc, 128, face);
        LOGFONTW logical = {};
        GetObjectW(font, sizeof(logical), &logical);
        const wchar_t glyphProbe[] = { 0x4e21, 0x5169, 0x4e24, L'A' };
        WORD glyphs[4] = {};
        GetGlyphIndicesW(dc, glyphProbe, 4, glyphs, GGI_MARK_NONEXISTING_GLYPHS);
        wchar_t decoded[8] = {};
        const char utf8Probe[] = { (char)0xe3, (char)0x81, (char)0x82 };
        int decodedCount = MultiByteToWideChar(932, 0, utf8Probe, 3, decoded, 8);
        const char mappingProbe[] = { (char)0xe4, (char)0xb8, (char)0xa1,
            (char)0xe5, (char)0x85, (char)0xa9, (char)0xe4, (char)0xb8, (char)0xa4 };
        wchar_t mapped[8] = {};
        int mappedCount = MultiByteToWideChar(CP_UTF8, 0, mappingProbe, 9, mapped, 8);
        std::wprintf(L"GDI face=%ls charset=%u height=%ld weight=%ld\n",
            face, (unsigned)logical.lfCharSet, logical.lfHeight, logical.lfWeight);
        std::printf("PROBE glyphs=%u,%u,%u,%u cp932_count=%d first=%04x\n",
            glyphs[0], glyphs[1], glyphs[2], glyphs[3], decodedCount, (unsigned)decoded[0]);
        std::printf("MAPPING count=%d codepoints=%04x,%04x,%04x\n", mappedCount,
            (unsigned)mapped[0], (unsigned)mapped[1], (unsigned)mapped[2]);
        std::fflush(stdout);
        SelectObject(dc, old);
        ReleaseDC(window, dc);
        DeleteObject(font);
        return 0;
    }
    if (message == WM_CLOSE) { DestroyWindow(window); return 0; }
    if (message == WM_DESTROY) { PostQuitMessage(0); return 0; }
    return DefWindowProcW(window, message, wp, lp);
}

int wmain(int argc, wchar_t** argv) {
    if (argc != 2) { std::fwprintf(stderr, L"Usage: smoke_host.exe FULL_DLL_PATH\n"); return 2; }
    SetProcessDPIAware();
    HINSTANCE instance = GetModuleHandleW(NULL);
    WNDCLASSW wc = {};
    wc.lpfnWndProc = HostProc;
    wc.hInstance = instance;
    wc.lpszClassName = L"SimpleFontHookENSmokeHost";
    RegisterClassW(&wc);
    HWND window = CreateWindowW(wc.lpszClassName, L"SimpleFontHookEN Smoke Host",
        WS_OVERLAPPEDWINDOW, 20, 20, 600, 300, NULL, NULL, instance, NULL);
    HMODULE module = LoadLibraryW(argv[1]);
    if (!module) { std::printf("LoadLibrary failed: %lu\n", GetLastError()); return 1; }
    auto timeGetTimeProxy = reinterpret_cast<DWORD(WINAPI*)()>(GetProcAddress(module, "timeGetTime"));
    if (!timeGetTimeProxy || !timeGetTimeProxy()) return 3;
    std::printf("Loaded DLL and forwarded timeGetTime successfully\n");
    std::fflush(stdout);
    SetTimer(window, 1, 500, NULL);
    MSG message = {};
    while (GetMessageW(&message, NULL, 0, 0) > 0) {
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }
    // The process owns the DLL until exit, matching the game deployment lifecycle.
    return 0;
}
