from aws_cdk import Stack, CfnOutput
from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import bedrock


class GuardrailStack(Stack):
    """Stack that creates a Bedrock Guardrail for the AI Chef assistant.

    Uses the L2 Guardrail construct from generative-ai-cdk-constructs.
    Configures 5 types of protection:
    - 3 topic denials (non-cooking topics)
    - Content filters (hate, violence, sexual, misconduct, prompt attacks)
    - PII entity detection with anonymization and blocking
    - Sensitive information regex patterns (CPF, phone)
    - Word filters (profanity + custom blocked words)
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        guardrail = bedrock.Guardrail(
            self,
            "ChefGuardrail",
            name="ai-chef-guardrail",
            description="Guardrail for AI Chef assistant - blocks non-cooking topics, filters harmful content, protects PII",
            blocked_input_messaging="Desculpe, nao posso ajudar com esse tipo de pergunta. Sou um chef de cozinha virtual e so posso ajudar com receitas e culinaria!",
            blocked_outputs_messaging="Desculpe, nao posso fornecer essa informacao. Sou especializado apenas em culinaria e receitas.",
        )

        # --- Topic Policy: 3 denied topics ---

        guardrail.add_denied_topic_filter(
            bedrock.Topic.custom(
                name="Medical-Advice",
                definition="Questions about medical treatments, medications, diagnoses, health conditions, or any form of medical advice",
                examples=[
                    "What medicine should I take for a headache?",
                    "Is this rash dangerous?",
                    "Can you diagnose my symptoms?",
                ],
            )
        )

        guardrail.add_denied_topic_filter(
            bedrock.Topic.custom(
                name="Financial-Advice",
                definition="Questions about investments, stock trading, cryptocurrency, tax strategies, or any form of financial advice",
                examples=[
                    "Should I invest in Bitcoin?",
                    "What stocks should I buy?",
                    "How can I avoid paying taxes?",
                ],
            )
        )

        guardrail.add_denied_topic_filter(
            bedrock.Topic.custom(
                name="Legal-Advice",
                definition="Questions about lawsuits, contracts, legal rights, disputes, suing someone, or advice requiring a lawyer",
                examples=[
                    "Can I sue my neighbor for noise?",
                    "Posso processar meu vizinho por barulho?",
                    "Preciso de um advogado para isso?",
                    "Quais sao meus direitos trabalhistas?",
                    "Como abrir um processo judicial?",
                ],
            )
        )

        # --- Content Filters ---

        guardrail.add_content_filter(
            type=bedrock.ContentFilterType.HATE,
            input_strength=bedrock.ContentFilterStrength.HIGH,
            output_strength=bedrock.ContentFilterStrength.HIGH,
        )
        guardrail.add_content_filter(
            type=bedrock.ContentFilterType.INSULTS,
            input_strength=bedrock.ContentFilterStrength.HIGH,
            output_strength=bedrock.ContentFilterStrength.HIGH,
        )
        guardrail.add_content_filter(
            type=bedrock.ContentFilterType.SEXUAL,
            input_strength=bedrock.ContentFilterStrength.HIGH,
            output_strength=bedrock.ContentFilterStrength.HIGH,
        )
        guardrail.add_content_filter(
            type=bedrock.ContentFilterType.VIOLENCE,
            input_strength=bedrock.ContentFilterStrength.HIGH,
            output_strength=bedrock.ContentFilterStrength.HIGH,
        )
        guardrail.add_content_filter(
            type=bedrock.ContentFilterType.MISCONDUCT,
            input_strength=bedrock.ContentFilterStrength.HIGH,
            output_strength=bedrock.ContentFilterStrength.HIGH,
        )
        guardrail.add_content_filter(
            type=bedrock.ContentFilterType.PROMPT_ATTACK,
            input_strength=bedrock.ContentFilterStrength.HIGH,
            output_strength=bedrock.ContentFilterStrength.NONE,
        )

        # --- PII Filters ---

        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.EMAIL,
            action=bedrock.GuardrailAction.ANONYMIZE,
        )
        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.PHONE,
            action=bedrock.GuardrailAction.ANONYMIZE,
        )
        guardrail.add_pii_filter(
            type=bedrock.pii_type.General.NAME,
            action=bedrock.GuardrailAction.ANONYMIZE,
        )
        guardrail.add_pii_filter(
            type=bedrock.pii_type.USASpecific.US_SOCIAL_SECURITY_NUMBER,
            action=bedrock.GuardrailAction.BLOCK,
        )
        guardrail.add_pii_filter(
            type=bedrock.pii_type.Finance.CREDIT_DEBIT_CARD_NUMBER,
            action=bedrock.GuardrailAction.BLOCK,
        )

        # --- Regex Patterns (Brazilian formats) ---

        guardrail.add_regex_filter(
            name="BrazilianCPF",
            description="Matches Brazilian CPF numbers (XXX.XXX.XXX-XX)",
            pattern=r"\d{3}\.\d{3}\.\d{3}-\d{2}",
            action=bedrock.GuardrailAction.BLOCK,
        )
        guardrail.add_regex_filter(
            name="BrazilianPhoneNumber",
            description="Matches Brazilian phone numbers with area code",
            pattern=r"\(?\d{2}\)?\s?\d{4,5}-?\d{4}",
            action=bedrock.GuardrailAction.ANONYMIZE,
        )

        # --- Word Filters ---

        guardrail.add_managed_word_list_filter(
            type=bedrock.ManagedWordFilterType.PROFANITY
        )
        guardrail.add_word_filter(text="hack")
        guardrail.add_word_filter(text="exploit")
        guardrail.add_word_filter(text="jailbreak")
        guardrail.add_word_filter(text="ignore previous instructions")
        guardrail.add_word_filter(text="advogado")
        guardrail.add_word_filter(text="processo judicial")
        guardrail.add_word_filter(text="direitos trabalhistas")
        guardrail.add_word_filter(text="processar meu vizinho")
        guardrail.add_word_filter(text="abrir processo")
        guardrail.add_word_filter(text="entrar na justica")

        # --- Versioning ---

        version = guardrail.create_version("Initial version")

        # Exports
        self.guardrail_id = guardrail.guardrail_id
        self.guardrail_arn = guardrail.guardrail_arn
        self.guardrail_version = version

        CfnOutput(self, "GuardrailId", value=guardrail.guardrail_id)
        CfnOutput(self, "GuardrailArn", value=guardrail.guardrail_arn)
