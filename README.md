# PJE Provisioner

Aplicativo desktop em Python (PySide6) para diagnosticar e simular correções do ambiente necessário ao **PJe**.

## Objetivo
O projeto centraliza, em uma interface gráfica simples, a verificação de componentes críticos do ambiente (token, drivers, PJe Office e navegadores) e oferece um fluxo de correção simulada para acelerar testes e validações da UI.

## Funcionalidades atuais
- Diagnóstico do ambiente com checklist visual.
- Barra de progresso para varredura e correções.
- Ícones de status (sucesso/erro) por componente.
- Botão de correção simulada com atualização em tempo real.
- Logging estruturado em JSON (console + arquivo).

## Status do projeto
- Versão atual focada em protótipo funcional da interface e orquestração.
- Parte das verificações/correções está simulada e preparada para evolução.

## Stack
- Python 3.12+
- PySide6
- PyYAML
- psutil
- colorlog

## Estrutura do projeto
```text
pje-provisioner/
├── app/
│   ├── core/                # Lógica de diagnóstico/correção
│   ├── ui/                  # Interface gráfica (PySide6)
│   ├── utils/               # Utilitários (logger, etc.)
│   └── main.py              # Entry point da aplicação
├── config/
│   └── config.yaml
├── drivers/
├── logs/                    # Logs JSON (gerados em execução)
├── requirements.txt
└── README.md
```

## Como executar
1. Criar e ativar ambiente virtual:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instalar dependências:
```bash
pip install -r requirements.txt
```

3. Executar aplicação:
```bash
python3 app/main.py
```

## Logging estruturado
O logger grava eventos JSON em:
- `logs/pje_provisioner.log`

Exemplo de evento:
```json
{"timestamp":"2026-02-27T15:51:11.094594+00:00","level":"INFO","logger":"pje_provisioner","message":"scan_started","event":"scan_started"}
```

## Próximos passos sugeridos
- Implementar verificações reais para token, driver e PJe Office.
- Substituir correções simuladas por ações reais com rollback seguro.
- Adicionar testes automatizados (unitários + integração).
- Empacotar para distribuição (Windows/Linux).

## Licença
Definir.
