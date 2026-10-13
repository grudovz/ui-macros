# Installs (or removes, with -Remove) a per-user Startup-folder shortcut that
# runs start_at_logon.vbs at every logon - no admin rights needed, since this
# only ever touches the current user's own Startup folder. start_at_logon.vbs
# does the actual work hidden (no console/taskbar windows); see its own
# comment header, and start_at_logon.bat, for the visible debug variant.
param(
    [switch]$Remove
)

$shortcutPath = Join-Path ([Environment]::GetFolderPath('Startup')) "ui-macros.lnk"

if ($Remove) {
    Remove-Item -Path $shortcutPath -ErrorAction SilentlyContinue
    Write-Host "Removed $shortcutPath"
    return
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $PSScriptRoot "start_at_logon.vbs"
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = "Start ui-macros hotkey listener + VS Code at logon (hidden)"
$shortcut.Save()
Write-Host "Created $shortcutPath -> $($shortcut.TargetPath)"
