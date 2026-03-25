#!/usr/bin/env python3
import aws_cdk as cdk

from stacks.guardrail_stack import GuardrailStack
from stacks.api_stack import ApiStack

app = cdk.App()

guardrail_stack = GuardrailStack(app, "ChefGuardrailStack")

api_stack = ApiStack(
    app,
    "ChefApiStack",
    guardrail_id=guardrail_stack.guardrail_id,
    guardrail_arn=guardrail_stack.guardrail_arn,
    guardrail_version=guardrail_stack.guardrail_version,
)
api_stack.add_dependency(guardrail_stack)

app.synth()
