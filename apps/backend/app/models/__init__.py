"""
SQLAlchemy Model Registry
=========================

Imports all domain models to ensure SQLAlchemy's MetaData can discover them
during Alembic autogeneration.
"""

from app.models.base import Base, TimestampedBase

# Domain: Customer
from app.models.customer import (
    Dealer,
    DealerAddress,
    DealerContact,
    DealerCreditLimit,
    DealerLanguagePreference,
    DealerPreferredWarehouse,
)

# Domain: Inventory
from app.models.inventory import Warehouse, Inventory, InventoryMovement

# Domain: Product
from app.models.product import (
    Brand,
    Category,
    Unit,
    GSTCategory,
    Product,
    ProductVariant,
    ProductPricing,
    ProductAlias,
)

# Domain: Order
from app.models.order import (
    DraftOrder,
    DraftOrderItem,
    Order,
    OrderVersion,
    OrderItem,
    OrderItemRemark,
    OrderStatusHistory,
    ERPJob,
    DeliveryTracking,
    PaymentStatus,
)

# Domain: Campaign
from app.models.campaign import (
    Campaign,
    CampaignRule,
    CampaignReward,
    CampaignEligibility,
    CampaignTarget,
    CampaignProduct,
    CampaignRegion,
    CampaignWarehouse,
    CampaignDealerGroup,
    CampaignUsage,
)

# Domain: IAM
from app.models.user import (
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    UserSession,
    RefreshToken,
    AuditLog,
)

# Domain: AI
from app.models.ai import (
    Conversation,
    ConversationTurn,
    ConversationSummary,
    Call,
    CallRecording,
    Transcript,
    SpeechSegment,
    CustomerMemory,
    ProductMemory,
    ConversationMemory,
    KnowledgeDocument,
    KnowledgeChunk,
    EmbeddingReference,
    ToolDefinition,
    ToolExecution,
    ToolResult,
    Recommendation,
    RecommendationFeedback,
    AIReasoning,
    PromptTemplate,
    PromptVersion,
    AIModel,
    ModelVersion,
)

# Explicit export of all models to prevent flake8/ruff unused import warnings
__all__ = [
    "Base",
    "TimestampedBase",
    "Dealer",
    "DealerAddress",
    "DealerContact",
    "DealerCreditLimit",
    "DealerLanguagePreference",
    "DealerPreferredWarehouse",
    "Warehouse",
    "Inventory",
    "InventoryMovement",
    "Brand",
    "Category",
    "Unit",
    "GSTCategory",
    "Product",
    "ProductVariant",
    "ProductPricing",
    "ProductAlias",
    "DraftOrder",
    "DraftOrderItem",
    "Order",
    "OrderVersion",
    "OrderItem",
    "OrderItemRemark",
    "OrderStatusHistory",
    "ERPJob",
    "DeliveryTracking",
    "PaymentStatus",
    "Campaign",
    "CampaignRule",
    "CampaignReward",
    "CampaignEligibility",
    "CampaignTarget",
    "CampaignProduct",
    "CampaignRegion",
    "CampaignWarehouse",
    "CampaignDealerGroup",
    "CampaignUsage",
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "UserSession",
    "RefreshToken",
    "AuditLog",
    "Conversation",
    "ConversationTurn",
    "ConversationSummary",
    "Call",
    "CallRecording",
    "Transcript",
    "SpeechSegment",
    "CustomerMemory",
    "ProductMemory",
    "ConversationMemory",
    "KnowledgeDocument",
    "KnowledgeChunk",
    "EmbeddingReference",
    "ToolDefinition",
    "ToolExecution",
    "ToolResult",
    "Recommendation",
    "RecommendationFeedback",
    "AIReasoning",
    "PromptTemplate",
    "PromptVersion",
    "AIModel",
    "ModelVersion",
]
