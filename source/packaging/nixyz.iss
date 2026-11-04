; Установщик NIXYZ. Собирается из build.py: версию и папки передаёт через /D.
;
; Inno Setup здесь только защищённая упаковка: распаковывает программу во временную папку, куда
; не-администратор не может писать, и запускает «NIXYZ.exe --install». Замена прежней версии, перенос
; настроек, ярлыки и запись в «Приложениях» — в installer.py, поэтому своего деинсталлятора Inno не ставит:
; удаляет программа сама («NIXYZ.exe --uninstall»).

[Setup]
AppId=NIXYZ
AppName=NIXYZ
AppVersion={#AppVersion}
AppPublisher=NIXYZ
VersionInfoVersion={#AppVersion}
VersionInfoDescription=Установка программы NIXYZ
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CreateAppDir=no
Uninstallable=no
CreateUninstallRegKey=no
DisableWelcomePage=yes
DisableReadyPage=yes
DisableFinishedPage=yes
DisableProgramGroupPage=yes
ShowLanguageDialog=no
LanguageDetectionMethod=uilanguage
WizardStyle=modern
SetupIconFile={#Icon}
OutputDir={#OutDir}
OutputBaseFilename=NIXYZ Setup
Compression=lzma2/ultra64
SolidCompression=yes
LZMANumBlockThreads=4

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"; LicenseFile: "{#Legal}\license.ru.rtf"
Name: "en"; MessagesFile: "compiler:Default.isl"; LicenseFile: "{#Legal}\license.en.rtf"

[CustomMessages]
ru.Placing=Устанавливаю NIXYZ…
en.Placing=Installing NIXYZ…

[Files]
Source: "{#Dist}\*"; DestDir: "{tmp}\app"; Flags: recursesubdirs createallsubdirs ignoreversion

[Run]
Filename: "{tmp}\app\NIXYZ.exe"; Parameters: "--install"; WorkingDir: "{tmp}\app"; StatusMsg: "{cm:Placing}"; Flags: waituntilterminated
