from aws_cdk import (
    Stack,
    Duration,
    Aws,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class ApiStack(Stack):
    """Stack that creates the Lambda function and API Gateway for the AI Chef.

    The Lambda receives a 'guardrail' query parameter (true/false) to
    demonstrate the difference between guarded and unguarded responses.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        guardrail_id: str,
        guardrail_arn: str,
        guardrail_version: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda function
        chef_fn = lambda_.Function(
            self,
            "ChefFunction",
            function_name="ai-chef-function",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda_fn"),
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "GUARDRAIL_ID": guardrail_id,
                "GUARDRAIL_VERSION": guardrail_version,
                "MODEL_ID": "us.amazon.nova-2-lite-v1:0",
            },
        )

        # Bedrock permissions - scoped to specific models
        chef_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:inference-profile/us.amazon.nova-2-lite-v1:0",
                    "arn:aws:bedrock:*::foundation-model/amazon.nova-2-lite-v1:0"
                ],
            )
        )


        # ApplyGuardrail - scoped to this specific guardrail
        chef_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:ApplyGuardrail"],
                resources=[guardrail_arn],
            )
        )

        # API Gateway REST API
        api = apigw.RestApi(
            self,
            "ChefApi",
            rest_api_name="AI Chef API",
            description="REST API for the AI Chef assistant with Bedrock Guardrails",
            deploy_options=apigw.StageOptions(stage_name="prod"),
        )

        chef_resource = api.root.add_resource("chef")
        chef_resource.add_method(
            "POST",
            apigw.LambdaIntegration(chef_fn, proxy=True),
        )
        chef_resource.add_cors_preflight(
            allow_origins=["*"],
            allow_methods=["POST", "OPTIONS"],
        )

        # Standalone guardrail check endpoint
        guardrail_resource = api.root.add_resource("check-guardrail")
        guardrail_resource.add_method(
            "POST",
            apigw.LambdaIntegration(chef_fn, proxy=True),
        )
        guardrail_resource.add_cors_preflight(
            allow_origins=["*"],
            allow_methods=["POST", "OPTIONS"],
        )

        CfnOutput(self, "ApiUrl", value=api.url)
        CfnOutput(
            self,
            "ChefEndpoint",
            value=f"{api.url}chef",
            description="POST with {\"message\": \"...\", \"guardrail\": true/false}",
        )
        CfnOutput(
            self,
            "GuardrailCheckEndpoint",
            value=f"{api.url}check-guardrail",
            description="POST with {\"text\": \"...\"} to test guardrail standalone",
        )
