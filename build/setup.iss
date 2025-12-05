; Script2WAVE Inno Setup Script
; [advice from AI] Windows 설치 프로그램 생성 스크립트
;
; 사용법:
;   1. Inno Setup 6 설치 (https://jrsoftware.org/isinfo.php)
;   2. 이 파일을 Inno Setup Compiler로 열기
;   3. Compile 버튼 클릭

#define MyAppName "Script2WAVE"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "RickySonYH"
#define MyAppURL "https://github.com/RickySonYH/Script2Wave_Json"
#define MyAppExeName "Script2WAVE.exe"

[Setup]
; 앱 정보
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 설치 경로
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; 출력 설정
OutputDir=..\dist
OutputBaseFilename=Script2WAVE-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes

; 권한
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; UI 설정
WizardStyle=modern
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; 기타
AllowNoIcons=yes
LicenseFile=..\LICENSE
InfoBeforeFile=..\README.md

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; PyInstaller 빌드 결과물 전체 복사
Source: "..\dist\Script2WAVE\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; storage 폴더 생성용 더미 파일
Source: "..\storage\*"; DestDir: "{app}\storage"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Dirs]
; [advice from AI] 데이터 저장 폴더 생성
Name: "{app}\storage"
Name: "{app}\storage\uploads"
Name: "{app}\storage\outputs"

[Icons]
; 시작 메뉴
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; 바탕화면 (선택적)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 설치 완료 후 실행
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 언인스톨 시 storage 폴더 삭제 (선택적으로 데이터 보존 가능)
Type: filesandordirs; Name: "{app}\storage"

[Code]
// [advice from AI] 설치 전 이전 버전 확인
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// 설치 완료 메시지
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 설치 완료 후 추가 작업 가능
  end;
end;

