"""Unit tests for CDK stacks."""

import aws_cdk as cdk
from aws_cdk import assertions

from stacks.guardrail_stack import GuardrailStack
from stacks.api_stack import ApiStack


class TestGuardrailStack:
    """Tests for the GuardrailStack."""

    def setup_method(self) -> None:
        self.app = cdk.App()
        self.stack = GuardrailStack(self.app, "TestGuardrailStack")
        self.template = assertions.Template.from_stack(self.stack)

    def test_guardrail_created(self) -> None:
        """Verify the Bedrock Guardrail resource exists."""
        self.template.resource_count_is("AWS::Bedrock::Guardrail", 1)

    def test_guardrail_version_created(self) -> None:
        """Verify the Guardrail Version resource exists."""
        self.template.resource_count_is("AWS::Bedrock::GuardrailVersion", 1)

    def test_ssm_parameter_created(self) -> None:
        """Verify the SSM Parameter for version tracking exists."""
        self.template.has_resource_properties(
            "AWS::SSM::Parameter",
            {"Name": "/chef-ai/guardrail-version"},
        )

    def test_guardrail_has_topic_policy(self) -> None:
        """Verify the guardrail has topic deny policies configured."""
        self.template.has_resource_properties(
            "AWS::Bedrock::Guardrail",
            assertions.Match.object_like(
                {
                    "TopicPolicyConfig": assertions.Match.object_like(
                        {
                            "TopicsConfig": assertions.Match.array_with(
                                [
                                    assertions.Match.object_like(
                                        {"Name": "Medical-Advice", "Type": "DENY"}
                                    ),
                                ]
                            )
                        }
                    )
                }
            ),
        )

    def test_guardrail_has_content_filters(self) -> None:
        """Verify content filters are configured."""
        self.template.has_resource_properties(
            "AWS::Bedrock::Guardrail",
            assertions.Match.object_like(
                {
                    "ContentPolicyConfig": assertions.Match.object_like(
                        {
                            "FiltersConfig": assertions.Match.array_with(
                                [
                                    assertions.Match.object_like({"Type": "HATE"}),
                                ]
                            )
                        }
                    )
                }
            ),
        )

    def test_guardrail_has_pii_config(self) -> None:
        """Verify PII detection is configured."""
        self.template.has_resource_properties(
            "AWS::Bedrock::Guardrail",
            assertions.Match.object_like(
                {
                    "SensitiveInformationPolicyConfig": assertions.Match.object_like(
                        {
                            "PiiEntitiesConfig": assertions.Match.array_with(
                                [
                                    assertions.Match.object_like(
                                        {"Type": "EMAIL", "Action": "ANONYMIZE"}
                                    ),
                                ]
                            )
                        }
                    )
                }
            ),
        )

    def test_guardrail_has_word_filters(self) -> None:
        """Verify word filters are configured."""
        self.template.has_resource_properties(
            "AWS::Bedrock::Guardrail",
            assertions.Match.object_like(
                {
                    "WordPolicyConfig": assertions.Match.object_like(
                        {
                            "ManagedWordListsConfig": assertions.Match.array_with(
                                [
                                    assertions.Match.object_like({"Type": "PROFANITY"}),
                                ]
                            )
                        }
                    )
                }
            ),
        )


class TestApiStack:
    """Tests for the ApiStack."""

    def setup_method(self) -> None:
        self.app = cdk.App()
        guardrail_stack = GuardrailStack(self.app, "TestGuardrailStack2")
        self.stack = ApiStack(
            self.app,
            "TestApiStack",
            guardrail_id=guardrail_stack.guardrail_id,
            guardrail_arn=guardrail_stack.guardrail_arn,
            guardrail_version_param_name=guardrail_stack.version_param_name,
        )
        self.template = assertions.Template.from_stack(self.stack)

    def test_lambda_created(self) -> None:
        """Verify the Lambda function exists with correct runtime."""
        self.template.has_resource_properties(
            "AWS::Lambda::Function",
            {"Runtime": "python3.12", "Handler": "handler.lambda_handler"},
        )

    def test_lambda_environment(self) -> None:
        """Verify Lambda has required environment variables."""
        self.template.has_resource_properties(
            "AWS::Lambda::Function",
            assertions.Match.object_like(
                {
                    "Environment": assertions.Match.object_like(
                        {
                            "Variables": assertions.Match.object_like(
                                {"MODEL_ID": "us.amazon.nova-2-lite-v1:0"}
                            )
                        }
                    )
                }
            ),
        )

    def test_api_gateway_created(self) -> None:
        """Verify API Gateway REST API exists."""
        self.template.resource_count_is("AWS::ApiGateway::RestApi", 1)

    def test_lambda_has_bedrock_permissions(self) -> None:
        """Verify Lambda role has Bedrock invoke permissions."""
        self.template.has_resource_properties(
            "AWS::IAM::Policy",
            assertions.Match.object_like(
                {
                    "PolicyDocument": assertions.Match.object_like(
                        {
                            "Statement": assertions.Match.array_with(
                                [
                                    assertions.Match.object_like(
                                        {
                                            "Action": "bedrock:InvokeModel",
                                            "Effect": "Allow",
                                        }
                                    ),
                                ]
                            )
                        }
                    )
                }
            ),
        )
