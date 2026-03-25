# Chef de Cozinha AI com Bedrock Guardrails (CDK Python)

Tutorial completo de como criar um assistente de culinária com **Amazon Bedrock** protegido por **Guardrails**, usando **AWS CDK** em Python com o construct L2 do pacote `generative-ai-cdk-constructs`.

## O que esse projeto faz?

Um assistente virtual de culinária (Chef AI) que responde perguntas sobre receitas e técnicas culinárias. O diferencial é a camada de proteção com **Bedrock Guardrails** que:

- **Bloqueia tópicos fora do escopo**: medicina, finanças, jurídico
- **Filtra conteúdo nocivo**: ódio, violência, conteúdo sexual, insultos, prompt injection
- **Protege dados sensíveis (PII)**: e-mail, telefone, nome (anonimiza) e CPF, cartão de crédito (bloqueia)
- **Filtra palavras proibidas**: profanidade + palavras customizadas (hack, exploit, jailbreak)
- **Detecta padrões sensíveis via regex**: CPF brasileiro, telefone brasileiro

## Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Client      │────▶│ API Gateway  │────▶│   Lambda         │────▶│   Bedrock    │
│  (curl/app)  │     │  REST API    │     │  ai-chef-function│     │  Nova Lite   │
└─────────────┘     └──────────────┘     └────────┬─────────┘     └──────────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │ Bedrock Guardrail │
                                          │   (L2 Construct)  │
                                          └──────────────────┘
```

### Stacks

| Stack | Recursos |
|-------|----------|
| `ChefGuardrailStack` | Guardrail (L2) com 5 tipos de proteção |
| `ChefApiStack` | Lambda Function, API Gateway REST API |

## Pré-requisitos

- Python 3.12+
- AWS CDK CLI (`npm install -g aws-cdk`)
- AWS CLI configurada com credenciais
- Acesso ao modelo **Amazon Nova Lite** habilitado no Bedrock (região us-east-1)

## Setup

```bash
# Clonar o repositório
git clone https://github.com/jvoltolini/bedrock-guardrails-cdk-tutorial.git
cd bedrock-guardrails-cdk-tutorial

# Criar e ativar virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Bootstrap do CDK (primeira vez na conta/região)
cdk bootstrap

# Deploy
cdk deploy --all --require-approval never
```

## Endpoints

### POST /chef: Conversar com o Chef AI

Envia uma mensagem para o assistente de culinária. O parâmetro `guardrail` controla se a proteção esta ativa.

**Com guardrail (padrão):**
```bash
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/prod/chef \
  -H "Content-Type: application/json" \
  -d '{"message": "Como fazer um risoto de cogumelos?", "guardrail": true}'
```

**Sem guardrail (para comparação):**
```bash
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/prod/chef \
  -H "Content-Type: application/json" \
  -d '{"message": "Me de conselhos sobre investimentos", "guardrail": false}'
```

### POST /check-guardrail: Testar o guardrail isoladamente

Usa a API `ApplyGuardrail` para validar texto **sem invocar o modelo**. Útil para pré-validação.

```bash
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/prod/check-guardrail \
  -H "Content-Type: application/json" \
  -d '{"text": "Meu CPF e 123.456.789-00", "source": "INPUT"}'
```

## Exemplos de teste

### Topico bloqueado (medicina)
```bash
curl -X POST .../prod/chef \
  -d '{"message": "Que remédio devo tomar para dor de cabeça?", "guardrail": true}'
```

### PII detectado
```bash
curl -X POST .../prod/check-guardrail \
  -d '{"text": "Meu email e chef@exemplo.com e meu CPF e 123.456.789-00"}'
```

### Palavra bloqueada
```bash
curl -X POST .../prod/check-guardrail \
  -d '{"text": "Como fazer jailbreak do sistema?"}'
```

### Pergunta legítima de culinária
```bash
curl -X POST .../prod/chef \
  -d '{"message": "Qual a diferença entre assar e grelhar?", "guardrail": true}'
```

## Estrutura do projeto

```
.
├── app.py                          # Entry point do CDK
├── cdk.json                        # Configuração do CDK
├── requirements.txt                # Dependencias Python
├── stacks/
│   ├── guardrail_stack.py          # Stack do Guardrail (L2 construct)
│   └── api_stack.py                # Stack da API (Lambda + API GW)
├── lambda_fn/
│   └── handler.py                  # Handler da Lambda
└── README.md
```

## Guardrails configurados

| Tipo | Configuração | Ação |
|------|-------------|------|
| **Tópicos negados** | Medicina, Finanças, Jurídico | DENY |
| **Filtros de conteúdo** | Odio, Insultos, Sexual, Violencia, Má conduta, Prompt Attack | HIGH (block) |
| **PII** | Email, Telefone, Nome | ANONYMIZE |
| **PII** | SSN, Cartão de crédito | BLOCK |
| **Regex** | CPF brasileiro (XXX.XXX.XXX-XX) | BLOCK |
| **Regex** | Telefone brasileiro | ANONYMIZE |
| **Palavras** | Profanidade (managed list) | BLOCK |
| **Palavras** | hack, exploit, jailbreak, ignore previous instructions | BLOCK |

## L2 Construct vs L1 (CfnGuardrail)

Este projeto usa o **construct L2** do pacote `cdklabs.generative-ai-cdk-constructs`. Comparado ao L1 (`CfnGuardrail`):

| Aspecto | L1 (CfnGuardrail) | L2 (Guardrail) |
|---------|-------------------|----------------|
| Sintaxe | Verbosa, mapeia CloudFormation 1:1 | Métodos fluidos (`add_content_filter`, `add_pii_filter`) |
| Versionamento | Manual (`CfnGuardrailVersion` + SSM Parameter) | `guardrail.create_version()` |
| IAM | Manual | `guardrail.grant_apply(role)` |
| Métricas | Manual (CloudWatch) | `guardrail.metric_invocations()` |

## Detalhes técnicos

### ApplyGuardrail standalone

O endpoint `/check-guardrail` demonstra o uso da API `ApplyGuardrail` que valida texto contra o guardrail **sem invocar o modelo Bedrock**. Casos de uso:
- Pre-validacao de input antes de enviar ao modelo (economia de custo)
- Validação de conteúdo gerado por outras fontes
- Pipeline de moderação de conteúdo

## Cleanup

```bash
cdk destroy --all
```

## Custo estimado

- **Lambda**: Free tier (1M requests/mes)
- **API Gateway**: Free tier (1M requests/mes por 12 meses)
- **Bedrock Nova Lite**: ~$0.06/1K input tokens, ~$0.24/1K output tokens
- **Bedrock Guardrails**: $0.75/1K text units (1 text unit = 1000 chars)

Para uso de tutorial/desenvolvimento, o custo fica em centavos.

## Licença

MIT
