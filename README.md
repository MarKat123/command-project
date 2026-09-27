# radiocontrol

A small CLI for sending rig-control commands (via `rigctld`'s TCP socket) to
drive radio settings — power levels, CW profile, break-in behavior, PC
keying, frequency, and a per-location `LOCATION` environment variable
(`CapeCod` / `Charlotte`).

All the actual commands live as plain functions in [src/radiocontrol.py](src/radiocontrol.py)
and are exposed as console scripts via `[project.scripts]` in
[pyproject.toml](pyproject.toml) (`p5`, `p20`, `p40`, `p60`, `p80`, `p100`,
`pmax`, `Scott`, `NoScott`, `PCOff`, `PCON`, `CapeCod`, `Charlotte`, `setCW`,
`ft`, `test`), plus a `t<band>c`/`t<band>s` family for band/mode changes
(`t160c`/`t160s` through `t10c`/`t10s`, and `t30c` with no `t30s` since 30m
has no phone allocation). Each `t<band>c`/`t<band>s` command sets the band,
mode, and frequency, caps power for that band (`pmax`), and runs `ft` (Full
Tune) so the antenna gets tuned as part of the band change — declining to
key the paddle and just pressing Enter leaves the rig on the new band/mode
without actually transmitting.

This file exists so that after this project sits untouched for weeks or
months, picking it back up doesn't require re-deriving any of this from
scratch.

## The two environments

There are deliberately **two separate installs** of this package on this
machine, for two different purposes. Don't merge them — keeping them apart
is what makes both the debugger and the command line behave predictably.

| | Dev / debug | "Real world" / daily use |
|---|---|---|
| Tool | `.venv` (project-local virtualenv) | [pipx](https://pipx.pypa.io/) |
| Install type | editable (`pip install -e .`) | frozen copy, rebuilt on demand |
| Reflects source edits | immediately | only after you reinstall |
| How commands are run | through VS Code's debugger, using the venv interpreter directly | via `.exe` shims in `C:\Users\MarkS\.local\bin`, on PATH |
| Purpose | setting breakpoints, stepping through code | actually operating the radio from a plain command prompt |

### Dev environment (`.venv`)

- Location: `.venv\Scripts\python.exe` (Python 3.13).
- Installed editable: `.venv\Scripts\python.exe -m pip install -e .`
- This requires the `[build-system]` / `[tool.setuptools]` tables in
  `pyproject.toml` — without them, `pip install -e .` silently degrades or
  installs to the wrong place. If `pip install -e .` in a fresh venv ever
  complains about not being able to find the package, check those tables are
  still intact first.
- **`.venv\Scripts` is intentionally NOT on PATH.** It was for a while
  during setup, but that made it shadow the pipx-installed "real world"
  commands of the same name. VS Code doesn't need it on PATH — its debug
  configs invoke `.venv`'s interpreter directly.

### Debugging in VS Code

Interpreter is pinned via `.vscode/settings.json`
(`python.defaultInterpreterPath` → `.venv\Scripts\python.exe`), so VS Code
should pick it automatically. If it doesn't, reload the window or reselect
it via `Ctrl+Shift+P` → "Python: Select Interpreter".

Two debug configs exist in `.vscode/launch.json`:

- **"Python: Debug entry point"** — the one you actually want most of the
  time. Set a breakpoint in whichever function you're interested in (e.g.
  `setCW()`), hit F5, pick this config, and when prompted type the function
  name (e.g. `setCW`). This runs `scripts/debug_entry.py`, which does:
  ```python
  import radiocontrol
  getattr(radiocontrol, name)()
  ```
  so the debugger is genuinely calling that function under `.venv`'s
  interpreter, with breakpoints live.

- **"Python: Debug radiocontrol module"** — runs `python -m radiocontrol`,
  which only executes the file's top-level code (constant definitions, etc.)
  and exits. **It does not call any function**, since there's no
  `if __name__ == "__main__":` dispatcher — so a breakpoint inside any
  function will never be hit with this config. It's only useful for a
  breakpoint on a top-level statement. This is expected behavior, not a bug
  — don't waste time re-diagnosing it later.

### "Real world" / production install (pipx)

Installed once via:
```
py -m pipx install . --backend pip
```
(`--backend pip` because pipx's default `uv` backend was outdated on this
machine at install time; if that's since been fixed, plain `pipx install .`
should work too.)

This builds a real wheel from `pyproject.toml`, puts it in its own isolated
venv under `pipx`'s managed venvs directory, and symlinks the resulting
`.exe`s into `C:\Users\MarkS\.local\bin`, which **is** on PATH (ahead of
everything else that matters). This is what actually runs when you type
`p5`, `setCW`, `CapeCod`, etc. from a plain command prompt.

**This copy is frozen at whatever `src/radiocontrol.py` looked like at
install time.** Editing the source does nothing to it. To pick up code
changes:
```
py -m pipx install --force .
```
run from the project root. Do this after making any change you want
available outside VS Code.

## Windows PATH notes (in case this ever looks broken again)

- Windows builds a new process's PATH as **System PATH, then User PATH**,
  in that order. `C:\Python314\` (a plain global Python install) is on the
  *System* PATH. `.local\bin` (pipx's shims) and other per-user paths are
  on the *User* PATH, so they only win when nothing earlier already
  provides a same-named file.
- **Don't `pip install` (or `pip install -e`) this package into any global
  interpreter** (`C:\Python314`, the standalone `Python313` under
  `AppData\Local\Programs\Python`, or with `--user`). This has happened by
  accident more than once and each time produced a stale, silently-wrong
  copy that shadowed the real one depending on PATH order and terminal
  session. The only two installs that should ever exist are the `.venv`
  editable one and the pipx one.
- If commands ever seem to run "the wrong version" (old behavior, missing
  a function you just added), the first thing to check is
  `where <command-name>` in a **freshly opened** terminal (PATH changes made
  via `[Environment]::SetEnvironmentVariable` don't affect already-open
  terminal sessions) — see which `.exe` answers and trace it back to which
  install produced it.

## Known quirks

- `pyproject.toml` declares `CapeCod` and `Charlotte` entry points; they set
  a `LOCATION` Windows user environment variable to `CAPECOD` / `CHARLOTTE`
  respectively via `set_user_env_var()` in `radiocontrol.py` (registry write
  + `WM_SETTINGCHANGE` broadcast, so new processes see it without a
  logoff/logon). `get_user_env_var()` reads straight from the registry
  rather than `os.environ`, since `os.environ` would only reflect the value
  at the time the *current* process started.

## History

Versions follow [SemVer](https://semver.org/) (`MAJOR.MINOR.PATCH`), tracked
in `pyproject.toml`'s `[project] version`, with a git tag (`vX.Y.Z`) marking
each point this project was archived. `git tag` lists all of them;
`git log v0.1.0..v0.2.0` shows exactly what changed between two.

- **v0.1.0** (untagged, historical; noted as `260824_1` before tagging
  started) — Fixed a bug in command formatting when sending via TCP socket
  (added `\n`). Rewrote command sending to go over the TCP socket instead of
  shelling out via the system. Added `setCW()` for a baseline CW operating
  profile. Minor tweaks to `Scott()`. Added `test()` as a placeholder for
  exercising the `pip install -e .` / entry-point setup.
- **v0.2.0** — Diagnosed and fixed a broken editable install (package had
  drifted into a stale, non-editable global copy); added `[build-system]`
  config; fixed a module-name typo in `launch.json`; added the
  `scripts/debug_entry.py` debug launcher; added `CapeCod()` / `Charlotte()`
  and the `LOCATION_VAR` env var helpers; set up the pipx production install
  described above; fixed a `setcwfrequency`/`setCWfrequency` case-mismatch
  bug in `setCW()`; reworked debug output to persist across separate
  command-line invocations via `checkdebug()` / `setdebug()` / `unsetdebug()`
  (registry-backed, replacing the old in-memory `DEBUG` global); added
  `ft()` for a basic full-tune sequence; adopted SemVer + git tags for
  versioning.
- **v0.3.0** — Added `panwidget`, a standalone console widget for the
  FTDX10/FT-710 panadapter power (`SS04`) level: reads it once, tracks it
  locally, sends absolute set commands on `+`/`-`, and resyncs on regaining
  window focus. Anchors its window to the upper-right of the screen on
  launch, but detects ConPTY-hosted terminals (VS Code integrated terminal,
  Windows Terminal) and skips that positioning there rather than corrupting
  the display. Added as its own module + entry point alongside
  `radiocontrol`, plus a VS Code debug config that runs it in an external
  terminal so the window-positioning code has a real console to work with.
- **v0.3.1** — Rewrote `ft()` (Full Tune) to be mode-agnostic instead of
  CW-only: it now reads the rig's current mode and power before touching
  anything (`getmode()` / `getpower()`, new alongside matching `setmode()` /
  `setpower()`), forces CW-U and low power for the actual tune, then restores
  exactly what was there on entry rather than hard-coding a return to 100W.
  Also force-selects VFO-A as primary on both entry and exit (a rig behavior
  that had previously caused confusion mid-operation when it silently ended
  up on VFO-B), and, discovered during live testing, reordered the entry
  sequence so the mode is forced to CW *before* the CW-gated `KR`/`BI`/`ST`
  writes — this rig silently no-ops those writes unless it's already in CW
  mode. Sets up `ft()` as a solid foundation for the upcoming band/mode
  `t<band><mode>()` command family (replacing `setCW()`'s buggy
  `setCWfrequency()` band-boundary logic), which depends on `ft()` working
  correctly from any starting mode.
- **v0.4.0** — Added the `t<band>c`/`t<band>s` command family (`t160c`/
  `t160s` through `t10c`/`t10s`, plus `t30c` with no `t30s`), driven by a new
  `BAND_PLAN` table of standard US amateur CW/SSB sub-band edges and default
  frequencies, replacing `setCWfrequency()`'s buggy hardcoded ranges
  entirely. `setCW()` is repurposed as a reusable CW settings bundle (no
  longer touches frequency); a new `setSSB()` is its SSB corollary, picking
  the correct sideband per band. Each `t<band>c`/`t<band>s` command also
  sets the panadapter span (5kHz CW / 20kHz SSB), caps power for the band via
  a new `pmax()` (also directly callable) driven by a `BAND_MAX_POWER` table
  reflecting house RFI sensitivities that vary by band, and — after several
  days of live use showed the operator wanting to tune essentially every
  time anyway — runs `ft()` at the end, so a band change leaves the rig
  tune-ready; declining to key the paddle and pressing Enter still leaves
  the rig correctly on the new band/mode/power.
  Also fixed, via live testing: `ft()`'s closing `AB;` (VFOB=VFOA) turns out
  to copy mode as well as frequency, so it now fires *after* restoring
  VFO-A's original mode rather than before, or VFO-B ended up stuck in the
  CW-U tuning mode; VFO-A-primary selection (`VS0;`) moved out of `ft()`'s
  entry sequence and into `setCW()`/`setSSB()` instead, since establishing
  which VFO is primary belongs with establishing the mode, not with the
  general-purpose tuning routine (`ft()` keeps its exit-side `VS0;` as a
  safety net for standalone calls).
  Separately, while chasing an intermittent hang traced to COM-port/rig
  power interruptions: sockets now get an explicit `close_socket()` via
  `atexit` (previously relied entirely on OS cleanup at process exit) and a
  5-second timeout, so a dropped connection now fails with an actionable
  message instead of hanging `recv()` forever; `getfrequency()` and
  `getpower()` also now handle malformed/empty rig responses by returning
  `None` instead of raising `ValueError`.
