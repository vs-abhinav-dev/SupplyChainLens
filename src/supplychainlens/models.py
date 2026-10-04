from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    PACKAGE_MISSING = "package_missing"
    INVALID_CONSTRAINT = "invalid_constraint"
    NON_REGISTRY = "non_registry"
    NO_SATISFYING_VERSION = "no_satisfying_version"


class Package(BaseModel):
    package_id: str = Field(
        description="Unique identifier for the package, "
        "e.g., 'npm:lodash'"
    )
    name: str = Field(description="Package name, e.g., 'lodash'")
    ecosystem: str = Field(default="npm", description="Ecosystem name")


class PackageVersion(BaseModel):
    node_id: str = Field(description="Unique node identifier, e.g., 'npm:lodash@4.17.21'")
    package_id: str = Field(description="Package identifier, e.g., 'npm:lodash'")
    name: str = Field(description="Package name")
    version: str = Field(description="Exact package version string, e.g., '4.17.21'")
    published_at: Optional[str] = Field(
        default=None,
        description="ISO format publication timestamp",
    )


class Dependency(BaseModel):
    source_node_id: str = Field(
        description="Source package version node id, "
        "e.g., 'npm:express@5.1.0'"
    )
    target_package: str = Field(description="Target package name, e.g., 'body-parser'")
    version_constraint: str = Field(description="Dependency version constraint, e.g., '^2.2.0'")
    dependency_type: str = Field(
        default="dependencies",
        description="Type of dependency: dependencies, "
        "devDependencies, peerDependencies, "
        "optionalDependencies",
    )


class ResolvedDependency(BaseModel):
    source_node_id: str = Field(
        description="Source package version node id, "
        "e.g., 'npm:express@5.1.0'"
    )
    target_package: str = Field(description="Target package name")
    version_constraint: str = Field(description="Requested version constraint")
    resolved_node_id: Optional[str] = Field(
        default=None,
        description="Resolved package version node id, "
        "e.g., 'npm:body-parser@2.2.0'"
    )
    resolution_status: ResolutionStatus = Field(
        description="Explicit resolution outcome status"
    )
