# POC-001 — Readiness de Pod

O laboratório usa Python 3.12+ e biblioteca padrão. A classe `ReadinessTools`
carrega uma fixture JSON versionada e expõe três consultas em memória:
`get_pod_status`, `get_events` e `get_endpoints`. O código fica fora do pacote
do serviço e da imagem. As observações são fictícias e seguem a sequência
descrita no [K8S-008](https://github.com/roger-oliveira86/kubernetes-from-scratch/pull/31).

## Executar a partir da raiz

```bash
python3 -m unittest discover -s tests -p test_poc_001.py -v

python3 - <<'PY'
import json
from poc_001.readiness import ReadinessTools, diagnose

print(json.dumps(diagnose(
    ReadinessTools(), scenario="not_ready", namespace="fictional-lab",
    pod="demo-blocked", service="demo-web",
), indent=2))
PY
```

## Contrato

Cada ferramenta recebe um objeto com `scenario`, `namespace`, `timeout_ms` e
exatamente um identificador. Status e eventos recebem `pod`. Endpoints recebe
`service`. O cenário é um dos três nomes da fixture. Identificadores usam
rótulos DNS de até 63 caracteres. O orçamento de cada consulta é um inteiro
de 1 a 1.000 ms.

O retorno tem `tool`, `state` e `evidence`. Os estados são `ok`,
`invalid_input`, `not_found`, `missing_evidence`, `invalid_fixture`,
`fixture_unavailable` e `timeout`. Uma lista vazia é uma observação válida.
Um valor JSON nulo marca evidência ausente na fixture. O orçamento é
verificado ao terminar a consulta síncrona em memória. A leitura inicial
limitada a 16 KiB ocorre fora desse orçamento.

O diagnóstico retorna `running_not_ready` ao correlacionar o Pod Running
com Ready falso, um evento de falha de readiness e a ausência de endpoints
prontos. Retorna `healthy` se o Pod Running estiver Ready e vinculado a um
endpoint pronto. Os demais casos resultam em `insufficient_evidence`.
A janela observada e a relação entre Pod e Service são dadas pela fixture.
Os resultados descrevem essas observações e a causa raiz fica em aberto.

## Limites

As consultas usam somente a fixture empacotada, sem rede, Kubernetes,
credenciais, escrita ou shell. O diagnóstico é uma regra fixa. Uma integração
futura com inferência local requer autorização e validação separadas.
