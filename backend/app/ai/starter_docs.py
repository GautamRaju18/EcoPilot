"""Starter ESG policy + goal templates given to a brand-new company so the
AI copilot and report have grounded content from day one. Owned by the AI zone
because these documents feed the RAG index."""

STARTER_POLICIES = [
    dict(
        title="Environmental Sustainability Policy",
        category="Environmental",
        version="1.0",
        document=(
            "Our organisation commits to reducing greenhouse-gas emissions by 25% "
            "within three years against the current baseline. Every department must "
            "track its electricity, fuel and travel emissions quarterly. We aim to "
            "source at least 40% of our energy from renewable providers and to divert "
            "70% of operational waste from landfill. All major purchases should include "
            "a carbon-impact assessment."
        ),
    ),
    dict(
        title="Corporate Social Responsibility Policy",
        category="Social",
        version="1.0",
        document=(
            "We encourage every employee to contribute at least 12 volunteer hours per "
            "year to approved community activities such as tree plantation, clean-up "
            "drives and education programs. Participation earns reward points and is "
            "recognised on the company leaderboard. We are committed to a diverse and "
            "inclusive workforce and require proof of participation before points are "
            "awarded."
        ),
    ),
    dict(
        title="Governance & Compliance Policy",
        category="Governance",
        version="1.0",
        document=(
            "The company maintains a zero-tolerance stance on bribery and corruption. "
            "Internal ESG audits are conducted at least twice a year, and every "
            "compliance issue must have a named owner and a resolution due date. "
            "High-severity issues are resolved within 30 days. The overall ESG score is "
            "weighted 40% Environmental, 30% Social and 30% Governance."
        ),
    ),
]

STARTER_GOALS = [
    dict(target_metric="Company-wide Emission Reduction", target_value=25, unit="%",
         current_value=8),
    dict(target_metric="Renewable Energy Share", target_value=40, unit="%",
         current_value=15),
]
