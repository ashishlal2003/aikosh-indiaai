"""
Policy Engine
Loads and applies configurable policy rules from YAML configuration
All rules are policy-driven, not hardcoded
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta


class PolicyEngine:
    """
    Policy engine that loads and applies MSMED Act rules
    All eligibility, validation, and negotiation rules come from policy configuration
    """
    
    def __init__(self, policy_config_path: Optional[str] = None, mandatory_docs_path: Optional[str] = None):
        """
        Initialize policy engine with configuration files
        
        Args:
            policy_config_path: Path to policy_rules.yaml
            mandatory_docs_path: Path to mandatory_docs.yaml
        """
        # Default paths
        if policy_config_path is None:
            policy_config_path = os.getenv(
                "POLICY_CONFIG_PATH",
                str(Path(__file__).parent.parent.parent / "config" / "policy_rules.yaml")
            )
        if mandatory_docs_path is None:
            mandatory_docs_path = os.getenv(
                "MANDATORY_DOCS_PATH",
                str(Path(__file__).parent.parent.parent / "config" / "mandatory_docs.yaml")
            )
        
        self.policy_config_path = policy_config_path
        self.mandatory_docs_path = mandatory_docs_path
        self.policy_config: Dict[str, Any] = {}
        self.mandatory_docs_config: Dict[str, Any] = {}
        self.policy_version: str = "1.0.0"
        self.last_loaded: Optional[datetime] = None
        
        self._load_policies()
    
    def _load_policies(self) -> None:
        """Load policy configuration from YAML files"""
        try:
            with open(self.policy_config_path, 'r', encoding='utf-8') as f:
                self.policy_config = yaml.safe_load(f) or {}
            
            with open(self.mandatory_docs_path, 'r', encoding='utf-8') as f:
                self.mandatory_docs_config = yaml.safe_load(f) or {}
            
            self.last_loaded = datetime.now()
            self.policy_version = self.policy_config.get('version', '1.0.0')
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Policy configuration file not found: {e}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing policy YAML: {e}")
    
    def reload_policies(self) -> None:
        """Reload policies from disk (useful when policies are updated)"""
        self._load_policies()
    
    # Eligibility Methods
    
    def check_eligibility(
        self,
        dispute_amount: float,
        invoice_date: datetime,
        has_msme_registration: bool,
        registration_type: Optional[str] = None
    ) -> tuple[bool, List[str]]:
        """
        Check if dispute meets MSMED Act eligibility criteria
        
        Returns:
            (is_eligible, list_of_errors)
        """
        errors = []
        eligibility_rules = self.policy_config.get('msmed_act', {}).get('eligibility', {})
        
        # Check MSME registration
        if eligibility_rules.get('requires_msme_registration', True):
            if not has_msme_registration:
                errors.append("MSME registration is required")
            elif registration_type:
                valid_types = eligibility_rules.get('valid_registration_types', [])
                if valid_types and registration_type not in valid_types:
                    errors.append(f"Registration type must be one of: {', '.join(valid_types)}")
        
        # Check minimum dispute amount
        min_amount = eligibility_rules.get('minimum_dispute_amount', 1.0)
        if dispute_amount < min_amount:
            errors.append(f"Dispute amount must be at least ₹{min_amount}")
        
        # Check maximum dispute amount
        max_amount = eligibility_rules.get('maximum_dispute_amount')
        if max_amount is not None and dispute_amount > max_amount:
            errors.append(f"Dispute amount cannot exceed ₹{max_amount}")
        
        return len(errors) == 0, errors
    
    def check_timeline_eligibility(
        self,
        invoice_date: datetime,
        payment_due_date: Optional[datetime] = None,
        current_date: Optional[datetime] = None
    ) -> tuple[bool, List[str]]:
        """
        Check if dispute meets timeline requirements
        
        Returns:
            (is_eligible, list_of_errors)
        """
        errors = []
        if current_date is None:
            current_date = datetime.now()
        
        timeline_rules = self.policy_config.get('msmed_act', {}).get('timelines', {})
        
        # Check maximum days from invoice
        max_days = timeline_rules.get('max_days_from_invoice', 365)
        days_since_invoice = (current_date - invoice_date).days
        if days_since_invoice > max_days:
            errors.append(f"Dispute must be filed within {max_days} days of invoice date")
        
        # Check minimum payment delay
        if payment_due_date:
            min_delay = timeline_rules.get('min_payment_delay_days', 45)
            days_delayed = (current_date - payment_due_date).days
            if days_delayed < min_delay:
                errors.append(f"Payment must be delayed by at least {min_delay} days before filing dispute")
        
        return len(errors) == 0, errors
    
    # Document Requirements
    
    def get_mandatory_documents(self, dispute_type: str) -> List[str]:
        """
        Get list of mandatory document names for a dispute type
        
        Args:
            dispute_type: One of 'payment_delay', 'partial_payment', 'quality_dispute'
        
        Returns:
            List of mandatory document names
        """
        docs_config = self.mandatory_docs_config.get('documents', {})
        
        # Common mandatory documents
        common_mandatory = [
            doc['name'] for doc in docs_config.get('common', {}).get('mandatory', [])
        ]
        
        # Type-specific mandatory documents
        type_specific = []
        if dispute_type in docs_config:
            type_specific = [
                doc['name'] for doc in docs_config.get(dispute_type, {}).get('mandatory', [])
            ]
        
        return common_mandatory + type_specific
    
    def get_optional_documents(self, dispute_type: str) -> List[Dict[str, Any]]:
        """
        Get list of optional documents for a dispute type
        
        Returns:
            List of optional document dictionaries with name and helpful_for info
        """
        docs_config = self.mandatory_docs_config.get('documents', {})
        
        # Common optional documents
        common_optional = docs_config.get('common', {}).get('optional', [])
        
        # Type-specific optional documents
        type_specific = []
        if dispute_type in docs_config:
            type_specific = docs_config.get(dispute_type, {}).get('optional', [])
        
        return common_optional + type_specific
    
    # Validation Rules
    
    def get_hard_block_rules(self) -> List[str]:
        """Get list of validation rules that cause hard blocking"""
        return self.policy_config.get('validation', {}).get('hard_blocks', [])
    
    def get_soft_warning_rules(self) -> List[str]:
        """Get list of validation rules that cause soft warnings"""
        return self.policy_config.get('validation', {}).get('soft_warnings', [])
    
    # Negotiation Rules
    
    def get_settlement_range(self, original_amount: float) -> tuple[float, float]:
        """
        Get legally bounded settlement range for negotiation
        
        Returns:
            (min_settlement_amount, max_settlement_amount)
        """
        negotiation_rules = self.policy_config.get('negotiation', {})
        min_percentage = negotiation_rules.get('min_settlement_percentage', 50.0)
        max_percentage = negotiation_rules.get('max_settlement_percentage', 100.0)
        
        min_amount = original_amount * (min_percentage / 100.0)
        max_amount = original_amount * (max_percentage / 100.0)
        
        return min_amount, max_amount
    
    def get_max_negotiation_rounds(self) -> int:
        """Get maximum number of negotiation rounds before escalation"""
        return self.policy_config.get('negotiation', {}).get('max_negotiation_rounds', 5)
    
    def get_negotiation_timeline(self) -> tuple[int, int]:
        """
        Get minimum and maximum days between negotiation rounds
        
        Returns:
            (min_days, max_days)
        """
        negotiation_rules = self.policy_config.get('negotiation', {})
        min_days = negotiation_rules.get('min_days_between_rounds', 3)
        max_days = negotiation_rules.get('max_days_between_rounds', 30)
        return min_days, max_days
    
    # Interest Calculation
    
    def calculate_interest(
        self,
        principal: float,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> float:
        """
        Calculate interest as per MSMED Act
        
        Args:
            principal: Principal amount
            start_date: Date from which interest starts
            end_date: Date until which interest is calculated (default: today)
        
        Returns:
            Interest amount
        """
        if end_date is None:
            end_date = datetime.now()
        
        interest_config = self.policy_config.get('msmed_act', {}).get('interest', {})
        annual_rate = interest_config.get('annual_rate', 18.0)
        compounding = interest_config.get('compounding', 'monthly')
        
        # Calculate days
        days = (end_date - start_date).days
        if days <= 0:
            return 0.0
        
        # Simple interest calculation (can be enhanced for compounding)
        # For now, using simple interest: P * R * T / 100
        years = days / 365.0
        interest = principal * (annual_rate / 100.0) * years
        
        return round(interest, 2)
    
    # Dispute Type Rules
    
    def get_dispute_type_rules(self, dispute_type: str) -> Dict[str, Any]:
        """Get rules specific to a dispute type"""
        dispute_types = self.policy_config.get('msmed_act', {}).get('dispute_types', {})
        return dispute_types.get(dispute_type, {})
    
    # Policy Metadata
    
    def get_policy_version(self) -> str:
        """Get current policy version"""
        return self.policy_version
    
    def get_last_loaded_time(self) -> Optional[datetime]:
        """Get when policies were last loaded"""
        return self.last_loaded

