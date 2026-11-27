# 005. Script anti-suspensão do Windows

Arquivos: `scripts/manter_acordado.ps1` e `scripts/manter_acordado.bat` (duplo clique).

## Problema
O PC entrava em suspensão/bloqueio por inatividade durante o treino. A aba do Colab perdia a conexão e o ambiente de execução caía.

## O que foi feito
- Chama `SetThreadExecutionState` (mesma API dos players de vídeo): impede suspensão e desligamento da tela **enquanto o script estiver aberto**. Não exige administrador e não altera nenhuma configuração do Windows.
- Se o usuário ficar ocioso por mais de 120 s, envia um movimento mínimo de mouse (1 px e volta) para zerar o contador de inatividade, que é o que dispara o bloqueio de tela. Enquanto o usuário usa o PC, o script não interfere.
- Opções: `-SemMouse`, `-LimiteOciosoSeg`, `-IntervaloSeg`, `-Horas` (encerra sozinho), `-Teste` (verificação em ~10 s).
- Ao fechar o script (ou Ctrl+C), tudo volta ao normal.

## Como usar
Dê duplo clique em `scripts\manter_acordado.bat` **antes** de iniciar o treino e deixe a janela aberta. Para limitar o tempo: `scripts\manter_acordado.bat -Horas 10`.

## Como foi verificado
- `-Teste`: bloqueio ativado; contador de inatividade medido; o toque no mouse **zerou o contador** (4,1 s, depois 7,1 s, depois 0,3 s).
- Execução real de poucos segundos: tocou o mouse ao detectar ociosidade, encerrou no horário e liberou o bloqueio.
- O arquivo foi gravado com BOM UTF-8 para o PowerShell 5.1 não corromper os acentos.

## Limitações
- **Não impede**: bloqueio manual (Win+L), fechar a tampa do notebook, hibernar/desligar pelo menu, nem bloqueio imposto por política da instituição.
- Não consegui confirmar, com `powercfg /requests` (exige administrador), que o Windows lista o bloqueio. A verificação foi indireta, pelo retorno da API e pelo contador de inatividade.
- Não evita o limite de inatividade do **próprio Colab** nem o limite de duração da sessão.
- Em notebooks na bateria, mantenha o carregador ligado: o script não controla a hibernação por bateria crítica.
