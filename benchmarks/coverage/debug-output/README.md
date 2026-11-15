# Filtered debug-output lifecycle representative

See `references/coverage/debug-output.md`. Actual Mesa core and ANGLE KHR routes pass known application-message/filter/group/label/error/lifetime checks. Forced-off safe fallback is separately executed on both. Only experiment-owned messages and IDs are retained; no driver/environment text or pointer addresses are published.
