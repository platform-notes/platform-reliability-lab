# AGENTS.md

Instruções para agentes de IA (Claude Code, Codex, etc.) trabalhando neste repositório.

## Escopo

- Uma tarefa por sessão, com critério de pronto definido antes de começar.
- Diff mínimo: altere apenas o necessário para a tarefa.
- Não altere workflows de CI/CD, dependências ou arquivos fora do escopo da tarefa sem autorização explícita.

## Validação antes do merge

- O check obrigatório do repositório deve passar: `checks` (workflow `verify.yml`).
- Quando houver imagem de runtime: Trivy deve reportar 0 vulnerabilidades HIGH/CRITICAL.
- Imagens de container devem ser fixadas por digest, não por tag mutável.
- Workloads devem rodar como non-root.

## Nunca

- Push direto na branch `main`.
- Publicar imagens no GHCR (pausa vigente).
- Commitar segredos, tokens, e-mail pessoal ou outros dados pessoais.
- Reescrever histórico (force-push, rebase de commits já publicados, etc.).

## Revisão

- Codex comenta no PR.
- Merge é feito pelo dono do repositório, apenas com CI verde.
