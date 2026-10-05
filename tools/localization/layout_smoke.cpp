// Native GDI checks for production picker geometry, text fitting, and hit tests.
#include "../../SimpleFontHook/framework.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <cstdio>
using std::min;
using std::max;

namespace Config {
    DWORD DetectedCharset = DEFAULT_CHARSET;
    bool EnableFontHeightScale = false, EnableFontWidthScale = false;
    bool EnableFontCharSpacing = false, EnableFontVerticalMetrics = false;
    bool EnableFontLineSpacing = false, EnableFontWeight = false;
    float FontHeightScale = 1.0f, FontWidthScale = 1.0f;
    int FontCharSpacing = 0, FontAscentPermille = 880, FontDescentPermille = -120;
    int FontLineSpacing = 0, FontWeight = FW_NORMAL;
    wchar_t ForcedFontNameW[LF_FACESIZE] = L"";
}

namespace FontPicker {
#include "../../SimpleFontHook/ui/internal/state/font_picker_state.cppinc"
#include "../../SimpleFontHook/ui/internal/state/font_picker_layout_geometry.cppinc"
#include "../../SimpleFontHook/ui/internal/state/font_picker_metric_layout.cppinc"
}
using namespace FontPicker;
static int checks = 0;
static void Check(bool result, const char* label) {
    ++checks;
    if (!result) { std::printf("FAIL: %s\n", label); std::exit(1); }
}

int main(int argc, char**) {
    HDC dc = GetDC(NULL);
    Check(dc != NULL, "screen DC");
    for (int height : { MIN_HEIGHT, 720, 900 }) {
        WINDOW_HEIGHT = height;
        for (float scale : { 0.7f, 1.0f, 1.8f }) {
            g_uiScale = scale;
            RecalcLayout();
            Check(WINDOW_WIDTH == 480 && MIN_WIDTH == 480 && MIN_HEIGHT == 640, "compact width and minimum");
            Check(VISIBLE_ITEMS >= 1 && ITEM_HEIGHT <= LIST_HEIGHT, "one complete scrollable row");
            for (int active = 0; active < 4; ++active) {
                g_textSubstitutionEnabled = (active & 1) != 0;
                g_codepageRedirectEnabled = (active & 2) != 0;
                for (int mode = 0; mode < g_textSubstitutionModeCount; ++mode) {
                    g_textSubstitutionModeIdx = mode;
                    for (int preset = 0; preset < g_codepageRedirectPresetCount; ++preset) {
                        g_codepageRedirectPresetIdx = preset;
                        PickerButtonRow row = GetMappingButtonRow(dc);
                        for (int i = 0; i < row.count; ++i) {
                            RECT r = row.rects[i];
                            if (argc > 1 && height == MIN_HEIGHT)
                                std::printf("ROW %.1f %d %d %d %d %ld %ld %ld %ld\n",
                                    scale, active, mode, preset, i, r.left, r.top, r.right, r.bottom);
                            Check(r.left >= 10 && r.right <= WINDOW_WIDTH - 10, "mapping row within window");
                            SelectObject(dc, row.fonts[i]);
                            SIZE extent = {};
                            GetTextExtentPoint32W(dc, row.labels[i], (int)wcslen(row.labels[i]), &extent);
                            Check(extent.cx + 16 == r.right - r.left && extent.cy <= 20, "row caption fits");
                            Check(TextSubstitutionHitTest(r.left, r.top) == i, "button top-left edge");
                            Check(TextSubstitutionHitTest(r.right - 1, r.bottom - 1) == i, "button bottom-right edge");
                            Check(TextSubstitutionHitTest(r.right, r.top) == -1, "button exclusive right edge");
                        }
                    }
                }
            }
            for (int enabled = 0; enabled < 2; ++enabled) {
                g_spoofEnabled = enabled != 0;
                for (int target = 0; target < g_spoofCharsetCount; ++target) {
                    g_spoofCharsetIdx = target;
                    PickerButtonRow row = GetSpoofButtonRow(dc);
                    for (int i = 0; i < row.count; ++i) {
                        RECT r = row.rects[i];
                        Check(SpoofBarHitTest(r.left, r.top) == i, "spoof left edge");
                        Check(SpoofBarHitTest(r.right - 1, r.bottom - 1) == i, "spoof right edge");
                    }
                }
            }
            MetricsRects metrics;
            GetMetricsRects(metrics);
            const RECT bounds[] = { metrics.descent.label, metrics.descent.value, metrics.autoBtn };
            const wchar_t* labels[] = { L"Desc", L"-2000", L"Match Ref" };
            for (int i = 0; i < 3; ++i) {
                SelectObject(dc, GetFittedPickerFont(dc, labels[i], bounds[i], SF(11), FW_BOLD, 2));
                SIZE extent = {};
                GetTextExtentPoint32W(dc, labels[i], (int)wcslen(labels[i]), &extent);
                Check(extent.cx <= bounds[i].right - bounds[i].left - 4, "metric text width");
                Check(extent.cy <= bounds[i].bottom - bounds[i].top - 4, "metric text height");
            }
        }
    }
    SelectObject(dc, GetStockObject(SYSTEM_FONT));
    ClearPickerFontCache();
    ReleaseDC(NULL, dc);
    std::printf("PASS: %d native GDI layout and hit-test assertions\n", checks);
    return 0;
}
