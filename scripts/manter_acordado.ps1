<#
.SYNOPSIS
    Impede o Windows de suspender, desligar a tela ou bloquear por inatividade enquanto o
    treino roda no Google Colab.

.DESCRIPTION
    1) Usa SetThreadExecutionState (a mesma API dos players de vídeo): bloqueia a suspensão
       e o desligamento da tela enquanto este script estiver aberto. Não precisa de admin
       e não altera nenhuma configuração do Windows: ao fechar o script, tudo volta ao normal.
    2) Se você ficar sem usar o PC por mais de -LimiteOciosoSeg, envia um movimento mínimo
       de mouse (1 pixel e volta) para zerar o contador de inatividade. É isso que evita o
       bloqueio de tela por inatividade (protetor de tela com senha). Enquanto você estiver
       usando o PC, o script não mexe em nada. Use -SemMouse para desligar esta parte.

    NÃO impede: bloqueio manual (Win+L), fechar a tampa do notebook, hibernar/desligar pelo
    menu, nem bloqueio imposto por política da empresa/escola (inatividade via GPO).

.PARAMETER LimiteOciosoSeg
    Segundos de inatividade do usuário antes de simular o movimento. Padrão: 120.

.PARAMETER IntervaloSeg
    De quanto em quanto tempo o script verifica/renova o bloqueio. Padrão: 30.

.PARAMETER SemMouse
    Só bloqueia suspensão/tela; nunca mexe no mouse.

.PARAMETER Horas
    Encerra sozinho depois de N horas (0 = até você fechar). Padrão: 0.

.PARAMETER Teste
    Executa um ciclo curto de verificação (~10 s) e sai com código 0 (ok) ou 1 (falhou).

.EXAMPLE
    .\scripts\manter_acordado.ps1
    .\scripts\manter_acordado.ps1 -Horas 10 -SemMouse
#>
[CmdletBinding()]
param(
    [int]$LimiteOciosoSeg = 120,
    [int]$IntervaloSeg = 30,
    [switch]$SemMouse,
    [double]$Horas = 0,
    [switch]$Teste
)

$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class PI6Acordado
{
    [DllImport("kernel32.dll")]
    static extern uint SetThreadExecutionState(uint esFlags);

    [StructLayout(LayoutKind.Sequential)]
    struct LASTINPUTINFO { public uint cbSize; public uint dwTime; }

    [DllImport("user32.dll")]
    static extern bool GetLastInputInfo(ref LASTINPUTINFO plii);

    [DllImport("user32.dll")]
    static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, UIntPtr dwExtraInfo);

    const uint ES_CONTINUOUS       = 0x80000000;
    const uint ES_SYSTEM_REQUIRED  = 0x00000001;
    const uint ES_DISPLAY_REQUIRED = 0x00000002;
    const uint MOUSEEVENTF_MOVE    = 0x0001;

    public static bool Bloquear()
    {
        return SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED) != 0;
    }

    public static void Liberar()
    {
        SetThreadExecutionState(ES_CONTINUOUS);
    }

    // Segundos desde o último teclado/mouse REAL do usuário (ou -1 se a API falhar).
    public static double SegundosOcioso()
    {
        LASTINPUTINFO li = new LASTINPUTINFO();
        li.cbSize = (uint)Marshal.SizeOf(typeof(LASTINPUTINFO));
        if (!GetLastInputInfo(ref li)) return -1;
        uint agora = unchecked((uint)Environment.TickCount);
        return unchecked(agora - li.dwTime) / 1000.0;
    }

    // Movimento relativo de 1 px e volta: zera o contador de inatividade sem deslocar o cursor.
    public static void Cutucar()
    {
        mouse_event(MOUSEEVENTF_MOVE, 1, 0, 0, UIntPtr.Zero);
        mouse_event(MOUSEEVENTF_MOVE, -1, 0, 0, UIntPtr.Zero);
    }
}
'@

function Log($msg) { Write-Host ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg) }

if ($Teste) {
    $falhas = 0
    if (-not [PI6Acordado]::Bloquear()) { Log 'FALHA: SetThreadExecutionState retornou 0'; $falhas++ } else { Log 'ok: bloqueio de suspensão/tela ativado' }
    $ocioso = [PI6Acordado]::SegundosOcioso()
    if ($ocioso -lt 0) { Log 'FALHA: GetLastInputInfo'; $falhas++ } else { Log ("ok: ocioso há {0:N1}s" -f $ocioso) }
    if (-not $SemMouse) {
        Start-Sleep -Seconds 2
        $antes = [PI6Acordado]::SegundosOcioso()
        Start-Sleep -Seconds 3
        $meio = [PI6Acordado]::SegundosOcioso()
        [PI6Acordado]::Cutucar()
        Start-Sleep -Milliseconds 300
        $depois = [PI6Acordado]::SegundosOcioso()
        Log ("contador de inatividade: antes={0:N1}s  3s depois={1:N1}s  após o toque={2:N1}s" -f $antes, $meio, $depois)
        if ($depois -ge $meio) { Log 'FALHA: o toque não zerou o contador de inatividade'; $falhas++ } else { Log 'ok: o toque zera o contador de inatividade' }
    }
    [PI6Acordado]::Liberar()
    Log 'bloqueio liberado'
    if ($falhas -eq 0) { Log 'TESTE OK'; exit 0 } else { Log "TESTE FALHOU ($falhas)"; exit 1 }
}

$fim = if ($Horas -gt 0) { (Get-Date).AddHours($Horas) } else { $null }
Write-Host ''
Write-Host '  Mantendo o PC acordado para o treino no Colab.' -ForegroundColor Cyan
Write-Host '  Deixe esta janela ABERTA. Para parar: Ctrl+C ou feche a janela.' -ForegroundColor Cyan
Write-Host ("  Movimento de mouse quando ocioso > {0}s: {1}" -f $LimiteOciosoSeg, $(if ($SemMouse) { 'DESLIGADO' } else { 'ligado' })) -ForegroundColor Cyan
if ($fim) { Write-Host ("  Encerra sozinho às {0:HH:mm}" -f $fim) -ForegroundColor Cyan }
Write-Host ''

$toques = 0
try {
    while ($true) {
        if (-not [PI6Acordado]::Bloquear()) { Log 'AVISO: não consegui renovar o bloqueio de suspensão' }
        if (-not $SemMouse) {
            $ocioso = [PI6Acordado]::SegundosOcioso()
            if ($ocioso -ge $LimiteOciosoSeg) {
                [PI6Acordado]::Cutucar()
                $toques++
                if ($toques -eq 1 -or $toques % 20 -eq 0) { Log ("PC ocioso há {0:N0}s: toque no mouse (#{1})" -f $ocioso, $toques) }
            }
        }
        if ($fim -and (Get-Date) -ge $fim) { Log "Tempo de $Horas h cumprido. Encerrando."; break }
        Start-Sleep -Seconds $IntervaloSeg
    }
}
finally {
    [PI6Acordado]::Liberar()
    Log 'Bloqueio liberado: o Windows volta a suspender normalmente.'
}
