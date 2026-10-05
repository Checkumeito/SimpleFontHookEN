# UPX Build Tool

This directory provides a pinned UPX 5.1.1 Win64 binary for compressing Win32 and
x64 Release DLLs. The Release Post-Build Event first compresses and verifies a
temporary copy, then replaces `winmm.dll` in the standard output directory only
after success. To debug with PDB files, first run `upx -d winmm.dll` on the
corresponding DLL, or rebuild with the environment variable
`SIMPLEFONTHOOK_SKIP_PACK=1` set.

- Source: <https://github.com/upx/upx/releases/tag/v5.1.1>
- Release package: `upx-5.1.1-win64.zip`
- Release package SHA-256: `FA5380BCA4C2718547AAA0134BC0D8A7FA27E102F0AC6371573D60D1C21D64DE`
- `upx.exe` SHA-256: `16A29ADBDF3B6FDE74C290205E24CCEB7BEF1A216941922AA73D2D808A699BBB`

License terms are stored in `LICENSE` and `COPYING` in this directory.
