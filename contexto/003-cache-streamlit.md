# 003. Cache do Streamlit: `unexpected keyword argument 'guiar_por_harmonia'`

## Problema
Depois da mudança 002, o app falhou ao gerar:
`TypeError: GeradorMusical.compor() got an unexpected keyword argument 'guiar_por_harmonia'`.

## Causa
`obter_gerador()` em `app.py` usa `@st.cache_resource`. O Streamlit recarrega o `app.py` a cada interação, mas **não** recarrega os módulos de `src/` nem refaz o objeto em cache. O servidor que já estava aberto continuava com a instância antiga de `GeradorMusical`, criada antes de `compor()` ganhar o parâmetro.

## O que foi alterado
- `app.py`: `obter_gerador(versao_codigo)` agora recebe a data de modificação mais recente dos arquivos de `src/`. Quando o código muda, o argumento muda e o cache é invalidado sozinho.

## Como foi verificado
Só foi verificado que `app.py` compila. Não foi aberto o app. O usuário confirmou depois que o app voltou a funcionar ("melhorou muito").

## Limitações
- Se um módulo de `src/` já foi importado pelo processo do Streamlit, a nova instância pode ainda usar o módulo antigo em memória. Por isso, depois de editar `src/`, **reinicie o `streamlit run`**.
