"""
settings.py
Corresponds to Java: AdProperties
Reads Azure AD configuration from environment variables or .env file
"""
from pydantic import Field
from pydantic_settings import BaseSettings


class ADProperties(BaseSettings):
    tenant: str = Field(..., description="Azure AD Tenant ID")
    client_id: str = Field(..., description="App Registration Client ID")
    client_secret: str = Field(..., description="App Registration Client Secret")
    app_registration_name: str = Field(
        default="azure", description="Name used in Spring client registration (legacy)"
    )
    group_prefix: str = Field(
        ..., description="AD group name prefix filter, e.g. 'R02_UG_'"
    )
    # groupName -> list of permissions
    # '&' is stored as 'SummComp' in YAML; transformGroupKeys restores it
    # e.g. {"R02_UG_Axiom_SDLC_AxiomAI-SummComp_Developer_SPI": ["read", "write"]}
    groups: dict[str, list[str]] = Field(
        default_factory=dict,
        description="AD group name -> permission list mapping"
    )

    model_config = {
        "env_prefix": "AD_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # Supports nested dict: AD_GROUPS='{"GroupA": ["read"]}'
        "env_nested_delimiter": "__",
    }
