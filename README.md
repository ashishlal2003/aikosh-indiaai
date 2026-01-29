# MSME Virtual Negotiation Assistant

AI-enabled Virtual Negotiation Assistant for MSME dispute resolution in India, aligned with Government of India requirements and public-sector deployment constraints.

## 🎯 Project Overview

This system addresses the critical cash-flow stress faced by Indian MSMEs due to delayed payments by buyers. It provides a guided, multilingual, policy-driven platform for dispute resolution that:

- **Reduces friction** at dispute initiation
- **Blocks incomplete submissions** with hard validation
- **Enables early settlement** through explainable, human-approved negotiation
- **Maintains full auditability** for government deployment

## 🏗️ Architecture

The system is built in 5 distinct layers:

1. **Intake & Eligibility Layer** - Guided intake with hard blocking
2. **Claim Intelligence Layer** - Dispute validation and classification
3. **Negotiation Intelligence Layer** - AI-mediated bilateral negotiation (suggestions only)
4. **Interaction & Drafting Layer** - Plain-language outputs and drafts
5. **Governance & Compliance Layer** - Audit trails, explainability, DPDP compliance

## 🚨 Core Principles

- **AI assists, humans decide** - No autonomous actions
- **Hard blocking** - Mandatory requirements enforced
- **Policy-driven** - All rules configurable
- **Full audit trail** - Every action logged
- **Public-sector ready** - Explainable, auditable, compliant

## 📋 Getting Started

### Prerequisites

- Python 3.9+
- Virtual environment (recommended)

### Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env`
2. Configure policy rules in `config/policy_rules.yaml`
3. Set up mandatory document requirements in `config/mandatory_docs.yaml`

## 📁 Project Structure

See `PROJECT_TRACKER.md` for detailed structure and progress tracking.

## 🔒 Security & Compliance

- DPDP-compliant data handling
- Full audit logging
- Human override at all stages
- No autonomous AI decisions

## 📝 Development Status

See `PROJECT_TRACKER.md` for current progress and roadmap.

## 🤝 Contributing

This is a government hackathon project. All code must:
- Be clear and auditable
- Follow conservative patterns
- Include full documentation
- Maintain audit trails

## 📄 License

[To be determined based on government requirements]

