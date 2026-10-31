; Inno Setup script for SerialPortTool.
;
; Build the executable first, then compile this script:
;     pyinstaller packaging.spec --noconfirm
;     iscc installer\SerialPortTool.iss
; tools\build_installer.ps1 runs both steps.
;
; Design notes
; ------------
; * Installs under %LOCALAPPDATA%\Programs and requests no elevation, so the
;   app can write its log/ folder next to the executable. Installing into
;   Program Files would make logging fail for a non-admin user.
; * The AppId GUID must never change, otherwise upgrades install side by side
;   instead of replacing the previous version.

#define MyAppName "SerialPortTool"
#define MyAppDisplayName "串口调试工具"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SerialPortTool"
#define MyAppExeName "SerialPortTool.exe"
#define ProjectRoot ".."

[Setup]
AppId={{8F3A2C41-7B6E-4D9A-9C55-1E7F2B6D4A30}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppDisplayName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription={#MyAppDisplayName} 安装程序
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppDisplayName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#ProjectRoot}\dist
OutputBaseFilename=SerialPortTool-{#MyAppVersion}-setup
SetupIconFile={#ProjectRoot}\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppDisplayName}
; The payload is a onefile PyInstaller exe, which is already deflate-compressed,
; so lzma only buys about 0.6 MB out of 43 MB. max is used instead of ultra64
; because the extra dictionary mostly costs build memory for no real gain.
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
; The Chinese translation ships separately from Inno Setup, so include it only
; when the compiler actually has it. Missing file must not break the build.
#if FileExists(AddBackslash(CompilerPath) + "Languages\ChineseSimplified.isl")
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#ProjectRoot}\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppDisplayName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppDisplayName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppDisplayName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppDisplayName}}"; Flags: nowait postinstall skipifsilent

[Code]
// Logs are user data: never delete them without asking.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  LogDir: String;
begin
  if CurUninstallStep <> usPostUninstall then
    Exit;

  LogDir := ExpandConstant('{app}\log');
  if not DirExists(LogDir) then
    Exit;

  // A silent uninstall cannot show a prompt, so it must not guess: keep the
  // files. Nobody is watching, and deleting recordings unasked is worse than
  // leaving one folder behind.
  if UninstallSilent then
    Exit;

  if MsgBox('同时删除日志文件吗？' + #13#10 +
            'Delete the recorded log files as well?',
            mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    DelTree(LogDir, True, True, True);
end;
