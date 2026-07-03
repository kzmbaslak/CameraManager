; Inno Setup Script - Kamera Yönetim Sistemi

#define AppName "Kamera Yonetimi Sistemi"
#define AppVersion "1.0.0"
#define AppPublisher "kzm"
#define AppExeName "Calistir.bat"

[Setup]
AppId={{D37E885B-7FB3-4CF5-9610-DFCFED1D5173}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName=C:\KameraYonetimi
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\customer_package
OutputBaseFilename=KameraYonetimi_Kurulum
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\customer_package\KameraYonetimi\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\scripts\cache\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: VcRedistNeedsInstall

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\backend\python\python.exe"; IconIndex: 0
Name: "{group}\Sistemi Durdur"; Filename: "{app}\Durdur.bat"
Name: "{group}\Kullanim Kilavuzu"; Filename: "{app}\BENIOKU.txt"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon; IconFilename: "{app}\backend\python\python.exe"; IconIndex: 0

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/q /norestart"; StatusMsg: "Microsoft Visual C++ Redistributable yukleniyor..."; Flags: waituntilterminated; Check: VcRedistNeedsInstall
Filename: "{app}\{#AppExeName}"; Description: "Kamera Yonetimi Sistemini Hemen Baslat"; Flags: postinstall nowait skipifsilent

[Code]
function VcRedistNeedsInstall: Boolean;
var
  Installed: Cardinal;
begin
  // HKLM64 checks the 64-bit registry. VC++ 2015-2022 registers "Installed" as a DWORD (1).
  if RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) then
  begin
    Result := (Installed <> 1);
  end
  else
  begin
    Result := True;
  end;
end;
