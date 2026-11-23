
#define MyAppName "ARIS"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "ARIS"
#define MyAppExeName "ARIS.exe"

[Setup]
AppId={{8F5E4D2A-7C31-4A96-B6D8-91F4E8A23710}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\RC Inventory
DefaultGroupName=ARIS
OutputDir=installer
OutputBaseFilename=ARIS_Setup_1.2.0

Compression=lzma
SolidCompression=yes

ArchitecturesInstallIn64BitMode=x64os
PrivilegesRequired=admin

UninstallDisplayIcon={app}\{#MyAppExeName}
AppVerName={#MyAppName} {#MyAppVersion}
UninstallDisplayName={#MyAppName}
VersionInfoDescription={#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoCompany={#MyAppPublisher}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные ярлыки:"; Flags: unchecked

[Files]
Source: "dist\RC_Inventory\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ARIS"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\ARIS"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить ARIS"; Flags: nowait postinstall skipifsilent
